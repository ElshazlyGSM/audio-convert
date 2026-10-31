import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

class CoverSearchResult {
  final String title;
  final String artist;
  final String imageUrl;

  CoverSearchResult({
    required this.title,
    required this.artist,
    required this.imageUrl,
  });
}

class CoverService {
  final ImagePicker _picker = ImagePicker();

  Future<String?> pickCustomCover() async {
    final XFile? image = await _picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 1400,
      maxHeight: 1400,
      imageQuality: 95,
    );
    return image?.path;
  }

  Future<List<CoverSearchResult>> searchItunesCovers(String query) async {
    if (query.trim().isEmpty) return [];
    try {
      final uri = Uri.parse(
        'https://itunes.apple.com/search?term=${Uri.encodeComponent(query)}&entity=song&limit=8',
      );
      final response = await http.get(uri).timeout(const Duration(seconds: 8));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final results = data['results'] as List<dynamic>? ?? [];
        final list = <CoverSearchResult>[];
        for (final item in results) {
          final trackName = item['trackName'] as String? ?? '';
          final artistName = item['artistName'] as String? ?? '';
          var artworkUrl = item['artworkUrl100'] as String? ?? '';
          if (artworkUrl.isNotEmpty) {
            // Replace 100x100 with 600x600 for high quality album artwork
            artworkUrl = artworkUrl.replaceAll('100x100bb.jpg', '600x600bb.jpg');
            list.add(
              CoverSearchResult(
                title: trackName,
                artist: artistName,
                imageUrl: artworkUrl,
              ),
            );
          }
        }
        return list;
      }
    } catch (_) {}
    return [];
  }

  Future<String?> downloadCoverToTemp(String imageUrl) async {
    try {
      final response = await http.get(Uri.parse(imageUrl)).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final tempDir = await getTemporaryDirectory();
        final filePath = p.join(
          tempDir.path,
          'cover_${DateTime.now().millisecondsSinceEpoch}.jpg',
        );
        final file = File(filePath);
        await file.writeAsBytes(response.bodyBytes);
        return file.path;
      }
    } catch (_) {}
    return null;
  }
}
