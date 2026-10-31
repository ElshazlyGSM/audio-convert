import 'dart:async';
import 'package:audioplayers/audioplayers.dart';

class AudioPlayerService {
  final AudioPlayer _player = AudioPlayer();

  Stream<Duration> get onPositionChanged => _player.onPositionChanged;
  Stream<Duration> get onDurationChanged => _player.onDurationChanged;
  Stream<PlayerState> get onPlayerStateChanged => _player.onPlayerStateChanged;

  PlayerState get state => _player.state;

  Future<void> play(String filePath) async {
    await _player.stop();
    await _player.play(DeviceFileSource(filePath));
  }

  Future<void> pause() async {
    await _player.pause();
  }

  Future<void> resume() async {
    await _player.resume();
  }

  Future<void> stop() async {
    await _player.stop();
  }

  Future<void> seek(Duration position) async {
    await _player.seek(position);
  }

  Future<Duration?> getDuration(String filePath) async {
    try {
      await _player.setSource(DeviceFileSource(filePath));
      return await _player.getDuration();
    } catch (_) {
      return null;
    }
  }

  void dispose() {
    _player.dispose();
  }
}
