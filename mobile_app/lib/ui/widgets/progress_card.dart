import 'package:flutter/material.dart';
import '../../l10n/app_strings.dart';
import '../../models/app_language.dart';

class ProgressCard extends StatefulWidget {
  final AppLanguage language;
  final bool isProcessing;
  final double currentProgress;
  final int currentIndex;
  final int totalFiles;
  final String currentFileName;
  final List<String> logs;
  final VoidCallback onCancel;

  const ProgressCard({
    super.key,
    required this.language,
    required this.isProcessing,
    required this.currentProgress,
    required this.currentIndex,
    required this.totalFiles,
    required this.currentFileName,
    required this.logs,
    required this.onCancel,
  });

  @override
  State<ProgressCard> createState() => _ProgressCardState();
}

class _ProgressCardState extends State<ProgressCard> {
  bool _showLogs = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final overallProgress = widget.totalFiles > 0
        ? ((widget.currentIndex + widget.currentProgress) / widget.totalFiles).clamp(0.0, 1.0)
        : 0.0;

    return Card(
      elevation: 3,
      color: theme.colorScheme.surfaceContainer,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.5,
                    color: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    AppStrings.tr('converting', widget.language),
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: theme.colorScheme.error,
                    side: BorderSide(color: theme.colorScheme.error),
                  ),
                  onPressed: widget.onCancel,
                  icon: const Icon(Icons.close, size: 16),
                  label: Text(AppStrings.tr('cancel', widget.language)),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Current file title
            Text(
              '${AppStrings.tr('current_file', widget.language)} (${widget.currentIndex + 1}/${widget.totalFiles}): ${widget.currentFileName}',
              style: theme.textTheme.bodyMedium,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),

            // Current file progress bar
            LinearProgressIndicator(
              value: widget.currentProgress > 0 ? widget.currentProgress : null,
              borderRadius: BorderRadius.circular(4),
              minHeight: 6,
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${(widget.currentProgress * 100).toStringAsFixed(1)}%',
                  style: theme.textTheme.labelSmall,
                ),
                Text(
                  '${AppStrings.tr('progress_overall', widget.language)}: ${(overallProgress * 100).toStringAsFixed(0)}%',
                  style: theme.textTheme.labelSmall,
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Toggle log viewer
            InkWell(
              onTap: () => setState(() => _showLogs = !_showLogs),
              child: Row(
                children: [
                  Icon(
                    _showLogs ? Icons.arrow_drop_up : Icons.arrow_drop_down,
                    size: 20,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Console Logs (${widget.logs.length})',
                    style: theme.textTheme.labelMedium?.copyWith(
                      color: theme.colorScheme.outline,
                    ),
                  ),
                ],
              ),
            ),

            if (_showLogs && widget.logs.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                height: 120,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.black.withAlpha(200),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: ListView.builder(
                  reverse: true,
                  itemCount: widget.logs.length,
                  itemBuilder: (context, index) {
                    final log = widget.logs[widget.logs.length - 1 - index];
                    return Text(
                      log,
                      style: const TextStyle(
                        color: Colors.greenAccent,
                        fontSize: 10,
                        fontFamily: 'monospace',
                      ),
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
}
