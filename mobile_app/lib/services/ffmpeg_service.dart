import 'dart:io';
import 'package:ffmpeg_kit_flutter_new/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new/return_code.dart';
import 'package:ffmpeg_kit_flutter_new/session.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../models/audio_preset.dart';
import '../models/conversion_options.dart';
import '../models/media_file.dart';

class ConversionTaskConfig {
  final MediaFile inputFile;
  final bool isVideoMode;
  final AudioFormat audioFormat;
  final String audioQuality;
  final VideoFormat videoFormat;
  final VideoCompressionPreset videoPreset;
  final VideoResolution videoResolution;
  final bool extractAudioFromVideo;
  final AudioPreset enhancementPreset;
  final double? trimStartSeconds;
  final double? trimEndSeconds;
  final bool keepFormatOnTrim;
  final String? coverImagePath;
  final bool embedCover;

  ConversionTaskConfig({
    required this.inputFile,
    required this.isVideoMode,
    required this.audioFormat,
    required this.audioQuality,
    required this.videoFormat,
    required this.videoPreset,
    required this.videoResolution,
    required this.extractAudioFromVideo,
    required this.enhancementPreset,
    this.trimStartSeconds,
    this.trimEndSeconds,
    this.keepFormatOnTrim = false,
    this.coverImagePath,
    this.embedCover = false,
  });
}

class FFmpegService {
  Session? _currentSession;

  Future<void> cancelCurrent() async {
    if (_currentSession != null) {
      await FFmpegKit.cancel(_currentSession!.getSessionId());
      _currentSession = null;
    }
  }

  Future<String?> processMedia({
    required ConversionTaskConfig config,
    void Function(double progress)? onProgress,
    void Function(String log)? onLog,
  }) async {
    final appDir = await getApplicationDocumentsDirectory();
    final outputDir = Directory(p.join(appDir.path, 'MediaStudioOutput'));
    if (!await outputDir.exists()) {
      await outputDir.create(recursive: true);
    }

    final inputPath = config.inputFile.path;
    final baseName = p.basenameWithoutExtension(inputPath);

    // Determine target extension
    String targetExt;
    if (config.isVideoMode && !config.extractAudioFromVideo) {
      if (config.videoFormat == VideoFormat.original) {
        targetExt = config.inputFile.extension;
      } else {
        targetExt = config.videoFormat.extension;
      }
    } else {
      if (config.keepFormatOnTrim && config.trimStartSeconds != null) {
        targetExt = config.inputFile.extension;
      } else {
        targetExt = config.audioFormat.extension;
      }
    }

    final outputPath = p.join(
      outputDir.path,
      '${baseName}_converted_${DateTime.now().millisecondsSinceEpoch}$targetExt',
    );

    final args = <String>[];

    // Overwrite output
    args.addAll(['-y']);

    // Trim start
    if (config.trimStartSeconds != null && config.trimStartSeconds! > 0) {
      args.addAll(['-ss', config.trimStartSeconds!.toStringAsFixed(3)]);
    }

    // Input file
    args.addAll(['-i', inputPath]);

    // Trim end
    if (config.trimEndSeconds != null && config.trimEndSeconds! > 0) {
      final double end = config.trimEndSeconds!;
      final double start = config.trimStartSeconds ?? 0;
      if (end > start) {
        args.addAll(['-to', end.toStringAsFixed(3)]);
      }
    }

    // Cover image input if requested
    final bool shouldEmbedCover = config.embedCover &&
        config.coverImagePath != null &&
        File(config.coverImagePath!).existsSync();

    if (shouldEmbedCover) {
      args.addAll(['-i', config.coverImagePath!]);
    }

    // Audio enhancement filter
    final filterGraph = config.enhancementPreset.filterGraph;

    // Check conversion mode: Video or Audio
    if (config.isVideoMode && !config.extractAudioFromVideo) {
      // VIDEO CONVERSION
      _buildVideoArgs(args, config, shouldEmbedCover, filterGraph);
    } else {
      // AUDIO CONVERSION (or Audio Extraction from Video)
      _buildAudioArgs(args, config, shouldEmbedCover, filterGraph, targetExt);
    }

    args.add(outputPath);

    final command = args.map((a) => a.contains(' ') ? '"$a"' : a).join(' ');
    onLog?.call('FFmpeg command: $command');

    final session = await FFmpegKit.executeAsync(
      command,
      (session) async {
        _currentSession = null;
      },
      (log) {
        onLog?.call(log.getMessage());
      },
      (stats) {
        if (config.inputFile.durationSeconds != null &&
            config.inputFile.durationSeconds! > 0) {
          final timeMs = stats.getTime();
          if (timeMs > 0) {
            final progress = (timeMs / 1000.0) / config.inputFile.durationSeconds!;
            onProgress?.call(progress.clamp(0.0, 1.0));
          }
        }
      },
    );

    _currentSession = session;
    final returnCode = await session.getReturnCode();

    if (ReturnCode.isSuccess(returnCode)) {
      final outFile = File(outputPath);
      if (await outFile.exists() && await outFile.length() > 0) {
        return outputPath;
      }
    }

    return null;
  }

  void _buildVideoArgs(
    List<String> args,
    ConversionTaskConfig config,
    bool hasCover,
    String? filterGraph,
  ) {
    final format = config.videoFormat;
    final preset = config.videoPreset;

    // Video codec & rate control
    if (format == VideoFormat.webm) {
      args.addAll(['-codec:v', 'libvpx-vp9', '-crf', preset.crfVp9, '-b:v', '0']);
      args.addAll(['-deadline', 'realtime', '-cpu-used', '4', '-row-mt', '1']);
      args.addAll(['-codec:a', 'libopus', '-b:a', preset.audioBitrate]);
    } else if (format == VideoFormat.avi || format == VideoFormat.wmv) {
      if (format == VideoFormat.avi) {
        args.addAll(['-codec:v', 'mpeg4', '-vtag', 'xvid', '-qscale:v', preset.qscale]);
        args.addAll(['-codec:a', 'libmp3lame', '-b:a', preset.audioBitrate]);
      } else {
        args.addAll(['-codec:v', 'wmv2', '-qscale:v', preset.qscale]);
        args.addAll(['-codec:a', 'wmav2', '-b:a', preset.audioBitrate]);
      }
    } else {
      // Default x264
      args.addAll([
        '-codec:v',
        'libx264',
        '-preset',
        'fast',
        '-crf',
        preset.crf,
        '-pix_fmt',
        'yuv420p',
      ]);
      if (format == VideoFormat.mp4 || format == VideoFormat.mov) {
        args.addAll(['-movflags', '+faststart']);
      }
      args.addAll(['-codec:a', 'aac', '-b:a', preset.audioBitrate]);
    }

    // Resolution scaling
    if (config.videoResolution.scale != null) {
      final scale = config.videoResolution.scale!;
      final parts = scale.split(':');
      final w = parts[0];
      final h = parts[1];
      args.addAll([
        '-vf',
        'scale=w=$w:h=$h:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2',
      ]);
    }

    // Audio filter in video
    if (filterGraph != null) {
      args.addAll(['-af', filterGraph]);
    }
  }

  void _buildAudioArgs(
    List<String> args,
    ConversionTaskConfig config,
    bool hasCover,
    String? filterGraph,
    String targetExt,
  ) {
    // If keep format on trim and no enhancement and no cover
    if (config.keepFormatOnTrim && filterGraph == null && !hasCover) {
      args.addAll(['-c', 'copy']);
      return;
    }

    // Check audio codec based on format
    switch (config.audioFormat) {
      case AudioFormat.mp3:
        args.addAll(['-codec:a', 'libmp3lame', '-b:a', config.audioQuality]);
        break;
      case AudioFormat.m4a:
        args.addAll(['-codec:a', 'aac', '-b:a', config.audioQuality]);
        break;
      case AudioFormat.aac:
        args.addAll(['-codec:a', 'aac', '-b:a', '192k']);
        break;
      case AudioFormat.wav:
        args.addAll(['-codec:a', 'pcm_s16le']);
        break;
      case AudioFormat.flac:
        args.addAll(['-codec:a', 'flac']);
        break;
      case AudioFormat.ogg:
        args.addAll(['-codec:a', 'libvorbis', '-b:a', '192k']);
        break;
      case AudioFormat.opus:
        args.addAll(['-codec:a', 'libopus', '-b:a', '128k']);
        break;
      case AudioFormat.wma:
        args.addAll(['-codec:a', 'wmav2', '-b:a', '192k']);
        break;
    }

    // Audio filter
    if (filterGraph != null) {
      args.addAll(['-af', filterGraph]);
    }

    // Cover embedding
    if (hasCover) {
      args.addAll(['-map', '0:a', '-map', '1:0']);
      if (targetExt == '.mp3') {
        args.addAll([
          '-id3v2_version',
          '3',
          '-metadata:s:v',
          'title="Album cover"',
          '-metadata:s:v',
          'comment="Cover (front)"',
        ]);
      } else {
        args.addAll(['-disposition:v:0', 'attached_pic']);
      }
    } else {
      // Discard video if extracting audio
      args.add('-vn');
    }
  }
}
