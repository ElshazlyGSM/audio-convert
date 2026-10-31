import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:share_plus/share_plus.dart';

import '../l10n/app_strings.dart';
import '../models/app_language.dart';
import '../models/audio_preset.dart';
import '../models/conversion_options.dart';
import '../models/media_file.dart';
import '../services/audio_player_service.dart';
import '../services/ffmpeg_service.dart';
import 'widgets/audio_options_card.dart';
import 'widgets/cover_art_card.dart';
import 'widgets/player_trim_card.dart';
import 'widgets/progress_card.dart';
import 'widgets/video_options_card.dart';
import 'widgets/youtube_download_dialog.dart';

class HomeScreen extends StatefulWidget {
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  const HomeScreen({
    super.key,
    required this.onToggleTheme,
    required this.isDarkMode,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  AppLanguage _language = AppLanguage.arabic;
  final AudioPlayerService _playerService = AudioPlayerService();
  final FFmpegService _ffmpegService = FFmpegService();

  final List<MediaFile> _selectedFiles = [];
  int _activeFileIndex = 0;

  // Options
  AudioFormat _audioFormat = AudioFormat.mp3;
  String _audioQuality = '320k';
  AudioPreset _audioPreset = AudioPreset.off;

  VideoFormat _videoFormat = VideoFormat.original;
  VideoCompressionPreset _videoCompression = VideoCompressionPreset.original;
  VideoResolution _videoResolution = VideoResolution.original;
  bool _extractAudioFromVideo = false;

  double? _trimStart;
  double? _trimEnd;
  bool _keepFormatOnTrim = false;

  String? _coverImagePath;
  bool _embedCover = false;

  // Conversion state
  bool _isProcessing = false;
  double _currentFileProgress = 0.0;
  int _currentProcessingIndex = 0;
  String _currentProcessingFileName = '';
  final List<String> _logs = [];
  final List<String> _completedFilePaths = [];

  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _playerService.dispose();
    _tabController.dispose();
    super.dispose();
  }

  MediaFile? get _activeFile {
    if (_selectedFiles.isEmpty || _activeFileIndex >= _selectedFiles.length) {
      return null;
    }
    return _selectedFiles[_activeFileIndex];
  }

  Future<void> _pickFiles() async {
    try {
      final result = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: [
          'mp3',
          'm4a',
          'aac',
          'wav',
          'flac',
          'ogg',
          'opus',
          'wma',
          'mp4',
          'mkv',
          'mov',
          'avi',
          'webm',
          'wmv',
          'flv',
          '3gp',
        ],
      );

      if (result.isNotEmpty) {
        final newFiles = <MediaFile>[];
        for (final f in result) {
          if (f.path != null) {
            final fileOnDisk = File(f.path!);
            final fileSize = fileOnDisk.existsSync() ? fileOnDisk.lengthSync() : 0;
            final duration = await _playerService.getDuration(f.path!);
            newFiles.add(
              MediaFile.fromPath(
                f.path!,
                fileSize,
                duration: duration != null ? duration.inMilliseconds / 1000.0 : null,
              ),
            );
          }
        }

        setState(() {
          _selectedFiles.clear();
          _selectedFiles.addAll(newFiles);
          _activeFileIndex = 0;
          _trimStart = null;
          _trimEnd = null;
        });
      }
    } catch (_) {}
  }

  Future<void> _startConversion() async {
    if (_selectedFiles.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppStrings.tr('no_files_selected', _language))),
      );
      return;
    }

    setState(() {
      _isProcessing = true;
      _currentFileProgress = 0.0;
      _currentProcessingIndex = 0;
      _logs.clear();
    });

    for (int i = 0; i < _selectedFiles.length; i++) {
      if (!_isProcessing) break;

      final file = _selectedFiles[i];
      setState(() {
        _currentProcessingIndex = i;
        _currentProcessingFileName = file.name;
        _currentFileProgress = 0.0;
      });

      final config = ConversionTaskConfig(
        inputFile: file,
        isVideoMode: file.isVideo && !_extractAudioFromVideo,
        audioFormat: _audioFormat,
        audioQuality: _audioQuality,
        videoFormat: _videoFormat,
        videoPreset: _videoCompression,
        videoResolution: _videoResolution,
        extractAudioFromVideo: _extractAudioFromVideo,
        enhancementPreset: _audioPreset,
        trimStartSeconds: _trimStart,
        trimEndSeconds: _trimEnd,
        keepFormatOnTrim: _keepFormatOnTrim,
        coverImagePath: _coverImagePath,
        embedCover: _embedCover,
      );

      final outputPath = await _ffmpegService.processMedia(
        config: config,
        onProgress: (p) {
          if (mounted) setState(() => _currentFileProgress = p);
        },
        onLog: (log) {
          if (mounted) {
            setState(() {
              _logs.add(log);
              if (_logs.length > 300) _logs.removeAt(0);
            });
          }
        },
      );

      if (outputPath != null) {
        setState(() {
          if (!_completedFilePaths.contains(outputPath)) {
            _completedFilePaths.insert(0, outputPath);
          }
        });
      }
    }

    if (mounted) {
      final wasCancelled = !_isProcessing;
      setState(() {
        _isProcessing = false;
        _currentFileProgress = 0.0;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            wasCancelled
                ? AppStrings.tr('conversion_cancelled', _language)
                : AppStrings.tr('conversion_finished', _language),
          ),
          backgroundColor: wasCancelled ? Colors.orange : Colors.green,
        ),
      );
    }
  }

  void _cancelConversion() {
    _ffmpegService.cancelCurrent();
    setState(() => _isProcessing = false);
  }

  void _openYouTubeDialog() {
    showDialog(
      context: context,
      builder: (_) => YouTubeDownloadDialog(
        language: _language,
        onDownloaded: (path) async {
          final file = File(path);
          if (await file.exists()) {
            final duration = await _playerService.getDuration(path);
            final mediaFile = MediaFile.fromPath(
              path,
              await file.length(),
              duration: duration != null ? duration.inMilliseconds / 1000.0 : null,
            );
            setState(() {
              _selectedFiles.insert(0, mediaFile);
              _activeFileIndex = 0;
            });
          }
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isArabic = _language.isArabic;

    return Directionality(
      textDirection: isArabic ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                AppStrings.tr('app_title', _language),
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
              ),
              Text(
                AppStrings.tr('app_subtitle', _language),
                style: theme.textTheme.bodySmall?.copyWith(fontSize: 11),
              ),
            ],
          ),
          actions: [
            // YouTube downloader button
            IconButton(
              icon: const Icon(Icons.video_collection, color: Colors.red),
              tooltip: AppStrings.tr('yt_title', _language),
              onPressed: _openYouTubeDialog,
            ),
            // Theme toggle
            IconButton(
              icon: Icon(widget.isDarkMode ? Icons.light_mode : Icons.dark_mode),
              onPressed: widget.onToggleTheme,
            ),
            // Language switcher popup
            PopupMenuButton<AppLanguage>(
              icon: const Icon(Icons.language),
              onSelected: (lang) => setState(() => _language = lang),
              itemBuilder: (_) => AppLanguage.values.map((l) {
                return PopupMenuItem(
                  value: l,
                  child: Row(
                    children: [
                      if (l == _language) ...[
                        const Icon(Icons.check, size: 16),
                        const SizedBox(width: 8),
                      ] else ...[
                        const SizedBox(width: 24),
                      ],
                      Text(l.label),
                    ],
                  ),
                );
              }).toList(),
            ),
          ],
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // File selection banner
                _buildFileSelectionCard(theme),
                const SizedBox(height: 12),

                // Active file player & trim controls
                if (_activeFile != null) ...[
                  PlayerTrimCard(
                    file: _activeFile!,
                    language: _language,
                    playerService: _playerService,
                    trimStart: _trimStart,
                    trimEnd: _trimEnd,
                    keepFormatOnTrim: _keepFormatOnTrim,
                    onTrimChanged: (s, e) {
                      setState(() {
                        _trimStart = s;
                        _trimEnd = e;
                      });
                    },
                    onKeepFormatChanged: (val) {
                      setState(() => _keepFormatOnTrim = val);
                    },
                  ),
                  const SizedBox(height: 12),
                ],

                // Tabs: Audio Options / Video Options / Cover Art
                Container(
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest.withAlpha(120),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: TabBar(
                    controller: _tabController,
                    indicatorSize: TabBarIndicatorSize.tab,
                    dividerColor: Colors.transparent,
                    tabs: [
                      Tab(
                        icon: const Icon(Icons.music_note, size: 20),
                        text: AppStrings.tr('tab_convert', _language),
                      ),
                      Tab(
                        icon: const Icon(Icons.movie, size: 20),
                        text: AppStrings.tr('mode_video', _language),
                      ),
                      Tab(
                        icon: const Icon(Icons.album, size: 20),
                        text: AppStrings.tr('tab_cover', _language),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Tab content
                AnimatedBuilder(
                  animation: _tabController,
                  builder: (context, _) {
                    switch (_tabController.index) {
                      case 0:
                        return AudioOptionsCard(
                          language: _language,
                          selectedFormat: _audioFormat,
                          selectedQuality: _audioQuality,
                          selectedPreset: _audioPreset,
                          onFormatChanged: (f) => setState(() => _audioFormat = f),
                          onQualityChanged: (q) => setState(() => _audioQuality = q),
                          onPresetChanged: (p) => setState(() => _audioPreset = p),
                        );
                      case 1:
                        return VideoOptionsCard(
                          language: _language,
                          selectedFormat: _videoFormat,
                          selectedCompression: _videoCompression,
                          selectedResolution: _videoResolution,
                          extractAudioOnly: _extractAudioFromVideo,
                          onFormatChanged: (f) => setState(() => _videoFormat = f),
                          onCompressionChanged: (c) => setState(() => _videoCompression = c),
                          onResolutionChanged: (r) => setState(() => _videoResolution = r),
                          onExtractAudioChanged: (val) =>
                              setState(() => _extractAudioFromVideo = val),
                        );
                      case 2:
                        return CoverArtCard(
                          language: _language,
                          coverPath: _coverImagePath,
                          embedCover: _embedCover,
                          onCoverSelected: (path) => setState(() => _coverImagePath = path),
                          onEmbedCoverChanged: (val) => setState(() => _embedCover = val),
                        );
                      default:
                        return const SizedBox.shrink();
                    }
                  },
                ),
                const SizedBox(height: 16),

                // Live Progress Card
                if (_isProcessing) ...[
                  ProgressCard(
                    language: _language,
                    isProcessing: _isProcessing,
                    currentProgress: _currentFileProgress,
                    currentIndex: _currentProcessingIndex,
                    totalFiles: _selectedFiles.length,
                    currentFileName: _currentProcessingFileName,
                    logs: _logs,
                    onCancel: _cancelConversion,
                  ),
                  const SizedBox(height: 16),
                ],

                // Action button: Start Processing
                SizedBox(
                  height: 52,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    onPressed: _isProcessing ? null : _startConversion,
                    icon: const Icon(Icons.play_arrow),
                    label: Text(
                      AppStrings.tr('start_conversion', _language),
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Completed Files Section
                if (_completedFilePaths.isNotEmpty) ...[
                  _buildCompletedFilesSection(theme),
                  const SizedBox(height: 30),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFileSelectionCard(ThemeData theme) {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _selectedFiles.isEmpty
                            ? AppStrings.tr('select_files', _language)
                            : '${AppStrings.tr('selected_files_count', _language)} (${_selectedFiles.length})',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        AppStrings.tr('select_files_sub', _language),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.outline,
                        ),
                      ),
                    ],
                  ),
                ),
                FilledButton.tonalIcon(
                  onPressed: _isProcessing ? null : _pickFiles,
                  icon: const Icon(Icons.folder_open),
                  label: Text(AppStrings.tr('select_files', _language)),
                ),
              ],
            ),

            if (_selectedFiles.isNotEmpty) ...[
              const SizedBox(height: 12),
              SizedBox(
                height: 40,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: _selectedFiles.length,
                  separatorBuilder: (context, index) => const SizedBox(width: 8),
                  itemBuilder: (context, idx) {
                    final f = _selectedFiles[idx];
                    final isSelected = idx == _activeFileIndex;
                    return ChoiceChip(
                      selected: isSelected,
                      label: Text(f.name, maxLines: 1),
                      avatar: Icon(
                        f.isVideo ? Icons.movie : Icons.audiotrack,
                        size: 16,
                      ),
                      onSelected: (_) {
                        setState(() {
                          _activeFileIndex = idx;
                          _trimStart = null;
                          _trimEnd = null;
                        });
                      },
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCompletedFilesSection(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.check_circle, color: Colors.green.shade600, size: 20),
            const SizedBox(width: 8),
            Text(
              '${AppStrings.tr('completed_files', _language)} (${_completedFilePaths.length})',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: _completedFilePaths.length,
          separatorBuilder: (context, index) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final path = _completedFilePaths[index];
            final file = File(path);
            final exists = file.existsSync();
            final sizeMb = exists ? (file.lengthSync() / (1024 * 1024)).toStringAsFixed(2) : '0';
            final fileName = p.basename(path);

            return Card(
              elevation: 1,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: theme.colorScheme.primaryContainer,
                  child: Icon(
                    MediaFile.checkIsVideo(p.extension(path))
                        ? Icons.videocam
                        : Icons.audiotrack,
                    color: theme.colorScheme.onPrimaryContainer,
                  ),
                ),
                title: Text(
                  fileName,
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: Text('$sizeMb MB'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.play_circle_outline),
                      tooltip: AppStrings.tr('open_file', _language),
                      onPressed: () {
                        _playerService.play(path);
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.share),
                      tooltip: AppStrings.tr('share_file', _language),
                      onPressed: () {
                        SharePlus.instance.share(ShareParams(files: [XFile(path)]));
                      },
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}
