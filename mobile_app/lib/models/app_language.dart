enum AppLanguage {
  arabic('ar', 'العربية'),
  english('en', 'English');

  final String code;
  final String label;

  const AppLanguage(this.code, this.label);

  bool get isArabic => this == AppLanguage.arabic;
}
