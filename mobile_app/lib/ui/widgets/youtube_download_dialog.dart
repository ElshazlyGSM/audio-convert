import 'package:flutter/material.dart';
import '../../l10n/app_strings.dart';
import '../../models/app_language.dart';
import '../../services/youtube_service.dart';

class YouTubeDownloadDialog extends StatefulWidget {
  final AppLanguage language;
  final ValueChanged<String> onDownloaded;

  const YouTubeDownloadDialog({
    super.key,
    required this.language,
    required this.onDownloaded,
  });

  @override
  State<YouTubeDownloadDialog> createState() => _YouTubeDownloadDialogState();
}

class _YouTubeDownloadDialogState extends State<YouTubeDownloadDialog> {
  final TextEditingController _urlController = TextEditingController();
  final YouTubeService _ytService = YouTubeService();

  YouTubeVideoInfo? _info;
  bool _loadingInfo = false;
  bool _isDownloading = false;
  double _downloadProgress = 0.0;
  String? _errorMessage;

  @override
  void dispose() {
    _urlController.dispose();
    _ytService.dispose();
    super.dispose();
  }

  Future<void> _fetchInfo() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) return;

    setState(() {
      _loadingInfo = true;
      _errorMessage = null;
      _info = null;
    });

    final info = await _ytService.fetchVideoInfo(url);

    if (mounted) {
      setState(() {
        _loadingInfo = false;
        if (info == null) {
          _errorMessage = 'Could not fetch video info. Check link and internet connection.';
        } else {
          _info = info;
        }
      });
    }
  }

  Future<void> _startDownload({required bool audioOnly}) async {
    final url = _urlController.text.trim();
    if (url.isEmpty) return;

    setState(() {
      _isDownloading = true;
      _downloadProgress = 0.0;
      _errorMessage = null;
    });

    final path = await _ytService.downloadMedia(
      url: url,
      audioOnly: audioOnly,
      onProgress: (p) {
        if (mounted) setState(() => _downloadProgress = p);
      },
    );

    if (mounted) {
      setState(() => _isDownloading = false);
      if (path != null) {
        widget.onDownloaded(path);
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppStrings.tr('done', widget.language)),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        setState(() {
          _errorMessage = 'Download failed. Please check internet connection.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      title: Row(
        children: [
          const Icon(Icons.video_collection, color: Colors.red),
          const SizedBox(width: 8),
          Text(AppStrings.tr('yt_title', widget.language)),
        ],
      ),
      content: SizedBox(
        width: double.maxFinite,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: _urlController,
                decoration: InputDecoration(
                  hintText: AppStrings.tr('yt_url_hint', widget.language),
                  border: const OutlineInputBorder(),
                  prefixIcon: const Icon(Icons.link),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.search),
                    onPressed: _loadingInfo || _isDownloading ? null : _fetchInfo,
                  ),
                ),
                onSubmitted: (_) => _fetchInfo(),
              ),
              const SizedBox(height: 12),

              if (_loadingInfo) ...[
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: CircularProgressIndicator(),
                  ),
                ),
              ],

              if (_errorMessage != null) ...[
                Text(
                  _errorMessage!,
                  style: TextStyle(color: theme.colorScheme.error, fontSize: 13),
                ),
                const SizedBox(height: 8),
              ],

              if (_info != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.network(
                          _info!.thumbnailUrl,
                          height: 140,
                          width: double.infinity,
                          fit: BoxFit.cover,
                          errorBuilder: (context, error, stackTrace) =>
                              const Icon(Icons.broken_image, size: 60),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _info!.title,
                        style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _info!.author,
                        style: theme.textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                if (_isDownloading) ...[
                  LinearProgressIndicator(value: _downloadProgress > 0 ? _downloadProgress : null),
                  const SizedBox(height: 8),
                  Center(
                    child: Text(
                      '${(_downloadProgress * 100).toStringAsFixed(1)}%',
                      style: theme.textTheme.labelMedium,
                    ),
                  ),
                  const SizedBox(height: 12),
                ] else ...[
                  FilledButton.icon(
                    onPressed: () => _startDownload(audioOnly: true),
                    icon: const Icon(Icons.music_note),
                    label: Text(AppStrings.tr('yt_download_audio', widget.language)),
                  ),
                  const SizedBox(height: 8),
                  FilledButton.tonalIcon(
                    onPressed: () => _startDownload(audioOnly: false),
                    icon: const Icon(Icons.video_file),
                    label: Text(AppStrings.tr('yt_download_video', widget.language)),
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isDownloading ? null : () => Navigator.pop(context),
          child: Text(AppStrings.tr('cancel', widget.language)),
        ),
      ],
    );
  }
}
