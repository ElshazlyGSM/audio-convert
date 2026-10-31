import 'package:flutter/material.dart';
import '../../l10n/app_strings.dart';
import '../../models/app_language.dart';
import '../../models/conversion_options.dart';

class VideoOptionsCard extends StatelessWidget {
  final AppLanguage language;
  final VideoFormat selectedFormat;
  final VideoCompressionPreset selectedCompression;
  final VideoResolution selectedResolution;
  final bool extractAudioOnly;
  final ValueChanged<VideoFormat> onFormatChanged;
  final ValueChanged<VideoCompressionPreset> onCompressionChanged;
  final ValueChanged<VideoResolution> onResolutionChanged;
  final ValueChanged<bool> onExtractAudioChanged;

  const VideoOptionsCard({
    super.key,
    required this.language,
    required this.selectedFormat,
    required this.selectedCompression,
    required this.selectedResolution,
    required this.extractAudioOnly,
    required this.onFormatChanged,
    required this.onCompressionChanged,
    required this.onResolutionChanged,
    required this.onExtractAudioChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isArabic = language.isArabic;

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
                Icon(Icons.video_library, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  AppStrings.tr('mode_video', language),
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Extract audio switch
            SwitchListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(
                AppStrings.tr('extract_audio', language),
                style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
              value: extractAudioOnly,
              onChanged: onExtractAudioChanged,
            ),
            const SizedBox(height: 8),

            if (!extractAudioOnly) ...[
              // Video format chips
              Text(
                AppStrings.tr('output_format', language),
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: VideoFormat.values.map((f) {
                  final isSelected = f == selectedFormat;
                  return ChoiceChip(
                    label: Text(f.getLabel(isArabic)),
                    selected: isSelected,
                    onSelected: (_) => onFormatChanged(f),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),

              // Compression preset dropdown
              Text(
                AppStrings.tr('video_compression', language),
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<VideoCompressionPreset>(
                initialValue: selectedCompression,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
                isExpanded: true,
                items: VideoCompressionPreset.values.map((preset) {
                  return DropdownMenuItem<VideoCompressionPreset>(
                    value: preset,
                    child: Text(
                      preset.getLabel(isArabic),
                      style: const TextStyle(fontSize: 14),
                    ),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) onCompressionChanged(val);
                },
              ),
              const SizedBox(height: 16),

              // Resolution dropdown
              Text(
                AppStrings.tr('video_resolution', language),
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<VideoResolution>(
                initialValue: selectedResolution,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
                isExpanded: true,
                items: VideoResolution.values.map((res) {
                  return DropdownMenuItem<VideoResolution>(
                    value: res,
                    child: Text(
                      res.getLabel(isArabic),
                      style: const TextStyle(fontSize: 14),
                    ),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) onResolutionChanged(val);
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
}
