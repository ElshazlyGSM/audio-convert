import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:youtube_explode_dart/youtube_explode_dart.dart';

class YouTubeVideoInfo {
  final String id;
  final String title;
  final String author;
  final Duration? duration;
  final String thumbnailUrl;
  final List<String> availableResolutions;

  YouTubeVideoInfo({
    required this.id,
    required this.title,
    required this.author,
    this.duration,
    required this.thumbnailUrl,
    required this.availableResolutions,
  });
}

class YouTubeService {
  final YoutubeExplode _yt = YoutubeExplode();

  Future<YouTubeVideoInfo?> fetchVideoInfo(String url) async {
    try {
      final video = await _yt.videos.get(url);
      final manifest = await _yt.videos.streamsClient.getManifest(video.id);

      final resolutions = <String>{};
      for (final s in manifest.video) {
        resolutions.add(s.videoQuality.name);
      }

      return YouTubeVideoInfo(
        id: video.id.value,
        title: video.title,
        author: video.author,
        duration: video.duration,
        thumbnailUrl: video.thumbnails.highResUrl,
        availableResolutions: resolutions.toList(),
      );
    } catch (_) {
      return null;
    }
  }

  Future<String?> downloadMedia({
    required String url,
    required bool audioOnly,
    String? selectedResolution,
    void Function(double progress)? onProgress,
  }) async {
    try {
      final video = await _yt.videos.get(url);
      final manifest = await _yt.videos.streamsClient.getManifest(video.id);

      final streamInfo = audioOnly
          ? manifest.audioOnly.withHighestBitrate()
          : manifest.muxed.withHighestBitrate();
      final extension = audioOnly ? '.m4a' : '.mp4';

      final appDir = await getApplicationDocumentsDirectory();
      final sanitizedTitle = video.title.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
      final targetPath = p.join(
        appDir.path,
        '$sanitizedTitle$extension',
      );

      final file = File(targetPath);
      final fileStream = file.openWrite();

      final stream = _yt.videos.streamsClient.get(streamInfo);
      final totalBytes = streamInfo.size.totalBytes;
      var downloadedBytes = 0;

      await for (final chunk in stream) {
        downloadedBytes += chunk.length;
        fileStream.add(chunk);
        if (onProgress != null && totalBytes > 0) {
          onProgress(downloadedBytes / totalBytes);
        }
      }

      await fileStream.flush();
      await fileStream.close();

      return targetPath;
    } catch (_) {
      return null;
    }
  }

  void dispose() {
    _yt.close();
  }
}
