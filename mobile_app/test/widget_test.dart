import 'package:flutter_test/flutter_test.dart';
import 'package:media_audio_studio_mobile/main.dart';

void main() {
  testWidgets('Media Audio Studio app smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const MediaAudioStudioApp());
    expect(find.byType(MediaAudioStudioApp), findsOneWidget);
  });
}
