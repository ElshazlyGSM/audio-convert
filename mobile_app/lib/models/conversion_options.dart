enum AudioFormat {
  mp3('MP3', '.mp3', 'libmp3lame'),
  m4a('M4A', '.m4a', 'aac'),
  aac('AAC', '.aac', 'aac'),
  wav('WAV', '.wav', 'pcm_s16le'),
  flac('FLAC', '.flac', 'flac'),
  ogg('OGG', '.ogg', 'libvorbis'),
  opus('OPUS', '.opus', 'libopus'),
  wma('WMA', '.wma', 'wmav2');

  final String label;
  final String extension;
  final String codec;

  const AudioFormat(this.label, this.extension, this.codec);
}

enum VideoFormat {
  original('Original Format', 'نفس الصيغة الأصلية', ''),
  mp4('MP4', 'MP4', '.mp4'),
  mkv('MKV', 'MKV', '.mkv'),
  avi('AVI', 'AVI', '.avi'),
  mov('MOV', 'MOV', '.mov'),
  webm('WEBM', 'WEBM', '.webm'),
  wmv('WMV', 'WMV', '.wmv'),
  flv('FLV', 'FLV', '.flv'),
  threeGp('3GP', '3GP', '.3gp');

  final String labelEn;
  final String labelAr;
  final String extension;

  const VideoFormat(this.labelEn, this.labelAr, this.extension);

  String getLabel(bool isArabic) => isArabic ? labelAr : labelEn;
}

enum VideoCompressionPreset {
  original(
    'Original (No compression)',
    'جودة أصلية (بدون ضغط)',
    '18',
    '2',
    '20',
    '320k',
  ),
  veryHigh(
    'Very High quality',
    'جودة عالية جداً',
    '20',
    '3',
    '24',
    '192k',
  ),
  high(
    'High quality',
    'جودة عالية',
    '24',
    '4',
    '28',
    '160k',
  ),
  medium(
    'Medium file',
    'حجم متوازن ومتوسط',
    '28',
    '6',
    '33',
    '128k',
  ),
  small(
    'Small file',
    'ملف صغير (توفير مساحة)',
    '32',
    '8',
    '38',
    '96k',
  ),
  verySmall(
    'Very Small file',
    'ملف صغير جداً (أقل حجم)',
    '36',
    '11',
    '44',
    '80k',
  );

  final String labelEn;
  final String labelAr;
  final String crf;
  final String qscale;
  final String crfVp9;
  final String audioBitrate;

  const VideoCompressionPreset(
    this.labelEn,
    this.labelAr,
    this.crf,
    this.qscale,
    this.crfVp9,
    this.audioBitrate,
  );

  String getLabel(bool isArabic) => isArabic ? labelAr : labelEn;
}

enum VideoResolution {
  original('Original size', 'الحجم الأصلي', null),
  res1080p('1080p Full HD', 'دقة 1080p فل إتش دي', '1920:1080'),
  res720p('720p HD', 'دقة 720p إتش دي', '1280:720'),
  res480p('480p SD', 'دقة 480p عادية', '854:480'),
  res360p('360p Low', 'دقة 360p منخفضة', '640:360');

  final String labelEn;
  final String labelAr;
  final String? scale;

  const VideoResolution(this.labelEn, this.labelAr, this.scale);

  String getLabel(bool isArabic) => isArabic ? labelAr : labelEn;
}

const List<String> audioQualityOptions = ['128k', '192k', '256k', '320k'];
