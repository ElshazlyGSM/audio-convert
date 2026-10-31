import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import '../../l10n/app_strings.dart';
import '../../models/app_language.dart';
import '../../models/media_file.dart';
import '../../services/audio_player_service.dart';

class PlayerTrimCard extends StatefulWidget {
  final MediaFile file;
  final AppLanguage language;
  final AudioPlayerService playerService;
  final double? trimStart;
  final double? trimEnd;
  final bool keepFormatOnTrim;
  final void Function(double? start, double? end) onTrimChanged;
  final void Function(bool keepFormat) onKeepFormatChanged;

  const PlayerTrimCard({
    super.key,
    required this.file,
    required this.language,
    required this.playerService,
    this.trimStart,
    this.trimEnd,
    required this.keepFormatOnTrim,
    required this.onTrimChanged,
    required this.onKeepFormatChanged,
  });

  @override
  State<PlayerTrimCard> createState() => _PlayerTrimCardState();
}

class _PlayerTrimCardState extends State<PlayerTrimCard> {
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;
  PlayerState _state = PlayerState.stopped;

  late TextEditingController _startController;
  late TextEditingController _endController;

  StreamSubscription? _posSub;
  StreamSubscription? _durSub;
  StreamSubscription? _stateSub;

  @override
  void initState() {
    super.initState();
    _startController = TextEditingController(
      text: widget.trimStart != null ? widget.trimStart!.toStringAsFixed(1) : '',
    );
    _endController = TextEditingController(
      text: widget.trimEnd != null ? widget.trimEnd!.toStringAsFixed(1) : '',
    );

    _posSub = widget.playerService.onPositionChanged.listen((p) {
      if (mounted) setState(() => _position = p);
    });
    _durSub = widget.playerService.onDurationChanged.listen((d) {
      if (mounted) setState(() => _duration = d);
    });
    _stateSub = widget.playerService.onPlayerStateChanged.listen((s) {
      if (mounted) setState(() => _state = s);
    });

    if (widget.file.durationSeconds != null && widget.file.durationSeconds! > 0) {
      _duration = Duration(milliseconds: (widget.file.durationSeconds! * 1000).toInt());
    }
  }

  @override
  void didUpdateWidget(covariant PlayerTrimCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.file.path != widget.file.path) {
      widget.playerService.stop();
      _position = Duration.zero;
      _startController.clear();
      _endController.clear();
      if (widget.file.durationSeconds != null) {
        _duration = Duration(milliseconds: (widget.file.durationSeconds! * 1000).toInt());
      }
    }
  }

  @override
  void dispose() {
    _posSub?.cancel();
    _durSub?.cancel();
    _stateSub?.cancel();
    _startController.dispose();
    _endController.dispose();
    super.dispose();
  }

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    if (d.inHours > 0) {
      return '${d.inHours.toString().padLeft(2, '0')}:$minutes:$seconds';
    }
    return '$minutes:$seconds';
  }

  void _markStart() {
    final currentSec = _position.inMilliseconds / 1000.0;
    _startController.text = currentSec.toStringAsFixed(1);
    widget.onTrimChanged(currentSec, widget.trimEnd);
  }

  void _markEnd() {
    final currentSec = _position.inMilliseconds / 1000.0;
    _endController.text = currentSec.toStringAsFixed(1);
    widget.onTrimChanged(widget.trimStart, currentSec);
  }

  void _resetTrim() {
    _startController.clear();
    _endController.clear();
    widget.onTrimChanged(null, null);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final maxSec = _duration.inMilliseconds > 0 ? _duration.inMilliseconds / 1000.0 : 1.0;
    final currentSec = (_position.inMilliseconds / 1000.0).clamp(0.0, maxSec);

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  widget.file.isVideo ? Icons.videocam : Icons.audiotrack,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.file.name,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    widget.file.formattedSize,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: theme.colorScheme.onPrimaryContainer,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Player timeline slider
            Slider(
              value: currentSec,
              min: 0.0,
              max: maxSec,
              onChanged: (val) {
                widget.playerService.seek(Duration(milliseconds: (val * 1000).toInt()));
              },
            ),

            // Time counters
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(_formatDuration(_position), style: theme.textTheme.bodySmall),
                  Text(_formatDuration(_duration), style: theme.textTheme.bodySmall),
                ],
              ),
            ),
            const SizedBox(height: 8),

            // Play / Pause controls
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton.filledTonal(
                  onPressed: () {
                    widget.playerService.seek(
                      Duration(milliseconds: ((currentSec - 5).clamp(0.0, maxSec) * 1000).toInt()),
                    );
                  },
                  icon: const Icon(Icons.replay_5),
                ),
                const SizedBox(width: 12),
                IconButton.filled(
                  iconSize: 32,
                  onPressed: () {
                    if (_state == PlayerState.playing) {
                      widget.playerService.pause();
                    } else {
                      widget.playerService.play(widget.file.path);
                    }
                  },
                  icon: Icon(
                    _state == PlayerState.playing ? Icons.pause : Icons.play_arrow,
                  ),
                ),
                const SizedBox(width: 12),
                IconButton.filledTonal(
                  onPressed: () {
                    widget.playerService.stop();
                  },
                  icon: const Icon(Icons.stop),
                ),
                const SizedBox(width: 12),
                IconButton.filledTonal(
                  onPressed: () {
                    widget.playerService.seek(
                      Duration(milliseconds: ((currentSec + 5).clamp(0.0, maxSec) * 1000).toInt()),
                    );
                  },
                  icon: const Icon(Icons.forward_5),
                ),
              ],
            ),
            const Divider(height: 28),

            // Trim controls
            Row(
              children: [
                Icon(Icons.content_cut, size: 20, color: theme.colorScheme.secondary),
                const SizedBox(width: 8),
                Text(
                  AppStrings.tr('tab_trim', widget.language),
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: _resetTrim,
                  icon: const Icon(Icons.refresh, size: 16),
                  label: Text(AppStrings.tr('reset_trim', widget.language)),
                ),
              ],
            ),
            const SizedBox(height: 8),

            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _markStart,
                    icon: const Icon(Icons.flag_outlined, size: 18),
                    label: Text(AppStrings.tr('mark_start', widget.language)),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _markEnd,
                    icon: const Icon(Icons.flag, size: 18),
                    label: Text(AppStrings.tr('mark_end', widget.language)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _startController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(
                      labelText: AppStrings.tr('start_time', widget.language),
                      isDense: true,
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (val) {
                      final s = double.tryParse(val);
                      widget.onTrimChanged(s, widget.trimEnd);
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: _endController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(
                      labelText: AppStrings.tr('end_time', widget.language),
                      isDense: true,
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (val) {
                      final e = double.tryParse(val);
                      widget.onTrimChanged(widget.trimStart, e);
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            SwitchListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(
                AppStrings.tr('keep_original_format', widget.language),
                style: theme.textTheme.bodyMedium,
              ),
              value: widget.keepFormatOnTrim,
              onChanged: widget.onKeepFormatChanged,
            ),
          ],
        ),
      ),
    );
  }
}
