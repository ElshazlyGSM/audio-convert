import 'package:path/path.dart' as p;

class MediaFile {
  final String path;
  final String name;
  final String extension;
  final int sizeBytes;
  final double? durationSeconds;
  final bool isVideo;

  const MediaFile({
    required this.path,
    required this.name,
    required this.extension,
    required this.sizeBytes,
    this.durationSeconds,
    required this.isVideo,
  });

  bool get isAudio => !isVideo;

  String get formattedSize {
    if (sizeBytes < 1024) return '$sizeBytes B';
    if (sizeBytes < 1024 * 1024) {
      return '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(sizeBytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }

  String get formattedDuration {
    if (durationSeconds == null) return '--:--';
    final totalSec = durationSeconds!.toInt();
    final minutes = totalSec ~/ 60;
    final seconds = totalSec % 60;
    final hours = minutes ~/ 60;
    if (hours > 0) {
      final remMin = minutes % 60;
      return '${hours.toString().padLeft(2, '0')}:${remMin.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    }
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  static bool checkIsVideo(String extension) {
    const videoExts = {
      '.mp4',
      '.mkv',
      '.mov',
      '.avi',
      '.webm',
      '.flv',
      '.wmv',
      '.m4v',
      '.3gp',
    };
    return videoExts.contains(extension.toLowerCase());
  }

  static bool checkIsAudio(String extension) {
    const audioExts = {
      '.mp3',
      '.m4a',
      '.aac',
      '.wav',
      '.flac',
      '.ogg',
      '.opus',
      '.wma',
    };
    return audioExts.contains(extension.toLowerCase());
  }

  factory MediaFile.fromPath(String filePath, int size, {double? duration}) {
    final ext = p.extension(filePath).toLowerCase();
    final name = p.basename(filePath);
    return MediaFile(
      path: filePath,
      name: name,
      extension: ext,
      sizeBytes: size,
      durationSeconds: duration,
      isVideo: checkIsVideo(ext),
    );
  }
}
