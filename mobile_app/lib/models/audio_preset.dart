enum AudioPreset {
  off('Off', 'إيقاف', []),
  normalizeVolume(
    'Normalize volume',
    'موازنة الصوت (Normalize)',
    ['loudnorm=I=-16:TP=-1.5:LRA=11'],
  ),
  louderAndClearer(
    'Louder and clearer',
    'صوت أعلى وأوضح',
    [
      'highpass=f=70',
      'lowpass=f=14000',
      'equalizer=f=3000:width_type=h:width=2500:g=3',
      'speechnorm=e=4:c=2:t=0.02',
      'loudnorm=I=-14:TP=-1.2:LRA=9',
    ],
  ),
  noiseReduction(
    'Noise reduction',
    'تقليل الضوضاء والتشويش',
    ['afftdn=nf=-30'],
  ),
  strongNoiseCleanup(
    'Strong noise cleanup',
    'تنقية قوية للضوضاء',
    [
      'highpass=f=90',
      'lowpass=f=11000',
      'afftdn=nf=-35',
      'anlmdn=s=0.0003:p=0.002:r=0.006:m=11',
      'speechnorm=e=3:c=2:t=0.02',
      'loudnorm=I=-16:TP=-1.5:LRA=10',
    ],
  ),
  podcastVoice(
    'Podcast voice',
    'صوت إذاعي / بودكاست',
    [
      'highpass=f=80',
      'lowpass=f=12500',
      'afftdn=nf=-30',
      'anlmdn=s=0.0002:p=0.002:r=0.006:m=11',
      'equalizer=f=180:width_type=h:width=120:g=-2',
      'equalizer=f=3500:width_type=h:width=2200:g=4',
      'speechnorm=e=5:c=2:t=0.015',
      'compand=attacks=0.05:decays=0.4:points=-80/-80|-45/-35|-18/-12|-6/-5|0/-3:soft-knee=6',
      'loudnorm=I=-14:TP=-1.2:LRA=8',
    ],
  ),
  reduceEcho(
    'Reduce echo',
    'تقليل الصدى',
    [
      'highpass=f=120',
      'lowpass=f=8500',
      'afftdn=nf=-32',
      'anlmdn=s=0.0004:p=0.002:r=0.008:m=15',
      'speechnorm=e=3:c=2:t=0.03',
    ],
  ),
  autoCleanAll(
    'Auto clean all',
    'تنظيف وتحسين شامل تلقائي',
    [
      'highpass=f=85',
      'lowpass=f=12000',
      'afftdn=nf=-34',
      'anlmdn=s=0.00035:p=0.002:r=0.008:m=13',
      'equalizer=f=200:width_type=h:width=160:g=-2',
      'equalizer=f=3200:width_type=h:width=2400:g=4',
      'speechnorm=e=5:c=2:t=0.015',
      'compand=attacks=0.05:decays=0.5:points=-80/-80|-45/-34|-20/-13|-6/-5|0/-3:soft-knee=6',
      'loudnorm=I=-14:TP=-1.2:LRA=8',
    ],
  );

  final String labelEn;
  final String labelAr;
  final List<String> filters;

  const AudioPreset(this.labelEn, this.labelAr, this.filters);

  String getLabel(bool isArabic) => isArabic ? labelAr : labelEn;

  String? get filterGraph {
    if (filters.isEmpty) return null;
    return filters.join(',');
  }
}
