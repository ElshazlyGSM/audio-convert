import os, glob
pats = ['*arab*', '*tahoma*', '*segoe*', '*trad*', '*simpbdo*', '*majalla*', '*cairo*', '*amiri*', '*dubai*', '*kufi*', '*naskh*', '*quran*', '*times*', '*impact*', '*trebuc*', '*georgia*', '*verdana*', '*alger*', '*hacen*', '*motken*', '*andalus*', '*andlso*', '*aldhabi*']
fonts = []
for p in pats:
    fonts.extend(glob.glob('C:/Windows/Fonts/' + p))
for f in sorted(set(os.path.basename(f) for f in fonts)):
    print(f)
