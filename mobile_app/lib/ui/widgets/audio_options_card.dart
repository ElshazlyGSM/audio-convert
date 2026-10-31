import 'package:flutter/material.dart';
import '../../l10n/app_strings.dart';
import '../../models/app_language.dart';
import '../../models/audio_preset.dart';
import '../../models/conversion_options.dart';

class AudioOptionsCard extends StatelessWidget {
  final AppLanguage language;
  final AudioFormat selectedFormat;
  final String selectedQuality;
  final AudioPreset selectedPreset;
  final ValueChanged<AudioFormat> onFormatChanged;
  final ValueChanged<String> onQualityChanged;
  final ValueChanged<AudioPreset> onPresetChanged;

  const AudioOptionsCard({
    super.key,
    required this.language,
    required this.selectedFormat,
    required this.selectedQuality,
    required this.selectedPreset,
    required this.onFormatChanged,
    required this.onQualityChanged,
    required this.onPresetChanged,
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
                Icon(Icons.music_note, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  AppStrings.tr('mode_audio', language),
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Target audio format chips
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
              children: AudioFormat.values.map((f) {
                final isSelected = f == selectedFormat;
                return ChoiceChip(
                  label: Text(f.label),
                  selected: isSelected,
                  onSelected: (_) => onFormatChanged(f),
                );
              }).toList(),
            ),
            const SizedBox(height: 16),

            // Bitrate options
            if (selectedFormat == AudioFormat.mp3 || selectedFormat == AudioFormat.m4a) ...[
              Text(
                AppStrings.tr('audio_quality', language),
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: audioQualityOptions.map((q) {
                  final isSelected = q == selectedQuality;
                  return ChoiceChip(
                    label: Text(q),
                    selected: isSelected,
                    onSelected: (_) => onQualityChanged(q),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),
            ],

            // Enhancement preset dropdown
            Text(
              AppStrings.tr('enhancement_preset', language),
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              AppStrings.tr('enhancement_desc', language),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<AudioPreset>(
              initialValue: selectedPreset,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              isExpanded: true,
              items: AudioPreset.values.map((preset) {
                return DropdownMenuItem<AudioPreset>(
                  value: preset,
                  child: Text(
                    preset.getLabel(isArabic),
                    style: const TextStyle(fontSize: 14),
                    overflow: TextOverflow.ellipsis,
                  ),
                );
              }).toList(),
              onChanged: (val) {
                if (val != null) onPresetChanged(val);
              },
            ),
          ],
        ),
      ),
    );
  }
}
