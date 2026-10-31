import 'dart:io';
import 'package:flutter/material.dart';
import '../../l10n/app_strings.dart';
import '../../models/app_language.dart';
import '../../services/cover_service.dart';

class CoverArtCard extends StatefulWidget {
  final AppLanguage language;
  final String? coverPath;
  final bool embedCover;
  final ValueChanged<String?> onCoverSelected;
  final ValueChanged<bool> onEmbedCoverChanged;

  const CoverArtCard({
    super.key,
    required this.language,
    required this.coverPath,
    required this.embedCover,
    required this.onCoverSelected,
    required this.onEmbedCoverChanged,
  });

  @override
  State<CoverArtCard> createState() => _CoverArtCardState();
}

class _CoverArtCardState extends State<CoverArtCard> {
  final CoverService _coverService = CoverService();
  bool _isSearching = false;

  Future<void> _pickFromGallery() async {
    final path = await _coverService.pickCustomCover();
    if (path != null) {
      widget.onCoverSelected(path);
    }
  }

  Future<void> _openSearchDialog() async {
    final textController = TextEditingController();
    List<CoverSearchResult> results = [];
    bool loading = false;

    await showDialog(
      context: context,
      builder: (dialogCtx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Text(AppStrings.tr('search_online', widget.language)),
              content: SizedBox(
                width: double.maxFinite,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: textController,
                      decoration: InputDecoration(
                        hintText: AppStrings.tr('search_query', widget.language),
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.search),
                          onPressed: () async {
                            if (textController.text.trim().isEmpty) return;
                            setDialogState(() => loading = true);
                            final res = await _coverService.searchItunesCovers(
                              textController.text.trim(),
                            );
                            setDialogState(() {
                              results = res;
                              loading = false;
                            });
                          },
                        ),
                      ),
                      onSubmitted: (_) async {
                        if (textController.text.trim().isEmpty) return;
                        setDialogState(() => loading = true);
                        final res = await _coverService.searchItunesCovers(
                          textController.text.trim(),
                        );
                        setDialogState(() {
                          results = res;
                          loading = false;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    if (loading)
                      const Padding(
                        padding: EdgeInsets.all(24),
                        child: CircularProgressIndicator(),
                      )
                    else if (results.isNotEmpty)
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxHeight: 280),
                        child: ListView.separated(
                          shrinkWrap: true,
                          itemCount: results.length,
                          separatorBuilder: (context, index) => const Divider(height: 1),
                          itemBuilder: (ctx, idx) {
                            final item = results[idx];
                            return ListTile(
                              leading: ClipRRect(
                                borderRadius: BorderRadius.circular(6),
                                child: Image.network(
                                  item.imageUrl,
                                  width: 48,
                                  height: 48,
                                  fit: BoxFit.cover,
                                  errorBuilder: (context, error, stackTrace) =>
                                      const Icon(Icons.broken_image),
                                ),
                              ),
                              title: Text(item.title, maxLines: 1),
                              subtitle: Text(item.artist, maxLines: 1),
                              onTap: () async {
                                Navigator.pop(dialogCtx);
                                setState(() => _isSearching = true);
                                final localPath = await _coverService.downloadCoverToTemp(
                                  item.imageUrl,
                                );
                                if (mounted) {
                                  setState(() => _isSearching = false);
                                  if (localPath != null) {
                                    widget.onCoverSelected(localPath);
                                  }
                                }
                              },
                            );
                          },
                        ),
                      ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogCtx),
                  child: Text(AppStrings.tr('cancel', widget.language)),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasCover = widget.coverPath != null && File(widget.coverPath!).existsSync();

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
                Icon(Icons.album, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  AppStrings.tr('tab_cover', widget.language),
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            SwitchListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(
                AppStrings.tr('embed_cover', widget.language),
                style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
              value: widget.embedCover,
              onChanged: widget.onEmbedCoverChanged,
            ),
            const SizedBox(height: 8),

            if (widget.embedCover) ...[
              Center(
                child: Container(
                  width: 140,
                  height: 140,
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: theme.colorScheme.outlineVariant),
                  ),
                  child: _isSearching
                      ? const Center(child: CircularProgressIndicator())
                      : hasCover
                          ? ClipRRect(
                              borderRadius: BorderRadius.circular(12),
                              child: Image.file(
                                File(widget.coverPath!),
                                fit: BoxFit.cover,
                              ),
                            )
                          : Center(
                              child: Icon(
                                Icons.image,
                                size: 48,
                                color: theme.colorScheme.outline,
                              ),
                            ),
                ),
              ),
              const SizedBox(height: 12),

              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _openSearchDialog,
                      icon: const Icon(Icons.search, size: 18),
                      label: Text(
                        AppStrings.tr('search_btn', widget.language),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _pickFromGallery,
                      icon: const Icon(Icons.photo_library, size: 18),
                      label: Text(
                        AppStrings.tr('pick_custom_cover', widget.language),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                ],
              ),
              if (hasCover) ...[
                const SizedBox(height: 8),
                Center(
                  child: TextButton.icon(
                    style: TextButton.styleFrom(foregroundColor: theme.colorScheme.error),
                    onPressed: () => widget.onCoverSelected(null),
                    icon: const Icon(Icons.delete_outline, size: 18),
                    label: Text(AppStrings.tr('remove_cover', widget.language)),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}
