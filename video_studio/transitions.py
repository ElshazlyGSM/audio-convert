"""
Video Transitions Engine for Multi-Clip NLE Timeline
Provides 45+ cinematic motion transitions using native FFmpeg `xfade` & `acrossfade`:
- Fades & Dissolves (Crossfade, Dip to Black, Flash White, Dreamy Fade)
- Motion & Push (Smooth Slide Left/Right/Up/Down, Push, Cover, Reveal)
- Zooms & Optics (Dynamic Zoom In, Iris Circle, Optical Distance, Motion Blur)
- Wipes & Slices (Horizontal/Vertical Wipes, Curtains Open/Close, Slices, Radial)
- Trendy & Glitch (Pixelize/Mosaic, Squeeze, Wind Sweeps)
Includes live PIL/NumPy animated preview simulation for instant GUI playback.

Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter


DEFAULT_TRANSITIONS_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "default_transition": "smoothleft",
    "default_duration": 0.5,
    "audio_crossfade": True,
    "apply_to_all": True,
    "clip_transitions": {},  # cut_index -> {"transition": str, "duration": float}
}

TRANSITION_CATEGORIES: Dict[str, Dict[str, str]] = {
    "all": {
        "label_ar": "✨ كل الانتقالات",
        "label_en": "✨ All Transitions",
        "icon": "✨",
    },
    "fade": {
        "label_ar": "💫 تلاشي وذوبان",
        "label_en": "💫 Fades & Dissolves",
        "icon": "💫",
    },
    "motion": {
        "label_ar": "🚀 حركات وانزلاق ودفع",
        "label_en": "🚀 Motion & Slides",
        "icon": "🚀",
    },
    "zoom": {
        "label_ar": "🔍 تكبير وعدسة وزوم",
        "label_en": "🔍 Zooms & Optics",
        "icon": "🔍",
    },
    "wipe": {
        "label_ar": "📐 مسح وستائر هندسية",
        "label_en": "📐 Wipes & Slices",
        "icon": "📐",
    },
    "trendy": {
        "label_ar": "⚡ عصري وسوشيال ميديا",
        "label_en": "⚡ Trendy & Social",
        "icon": "⚡",
    },
}

TRANSITION_PRESETS: Dict[str, Dict[str, Any]] = {
    # ---------------- 1. Fades & Dissolves ----------------
    "fade": {
        "key": "fade",
        "label_ar": "تلاشي متقاطع (Crossfade)",
        "label_en": "Classic Crossfade",
        "category": "fade",
        "icon": "💫",
        "desc_ar": "التلاشي الكلاسيكي الأكثر استخداماً عالمياً لربط المشاهد بنعومة فائقة",
        "desc_en": "Standard smooth crossfade between two scenes",
        "default_duration": 0.5,
        "is_popular": True,
    },
    "fadeblack": {
        "key": "fadeblack",
        "label_ar": "تلاشي إلى أسود سينمائي (Dip to Black)",
        "label_en": "Dip to Black",
        "category": "fade",
        "icon": "🎬",
        "desc_ar": "تلاشي سينمائي ينخفض للظلام ثم يفتح على المشهد التالي للفصول والرواية",
        "desc_en": "Cinematic dip to black, ideal for dramatic scene changes",
        "default_duration": 0.6,
        "is_popular": True,
    },
    "fadewhite": {
        "key": "fadewhite",
        "label_ar": "وميض أبيض ناعم (Flash White)",
        "label_en": "Flash to White",
        "category": "fade",
        "icon": "⚡",
        "desc_ar": "وميض ضوئي خاطف يضفي طاقة وإثارة بين اللقطات السريعة",
        "desc_en": "High energy flash transition, popular in music & reels",
        "default_duration": 0.35,
        "is_popular": True,
    },
    "dissolve": {
        "key": "dissolve",
        "label_ar": "ذوبان فيلمي ناعم (Film Dissolve)",
        "label_en": "Film Dissolve",
        "category": "fade",
        "icon": "✨",
        "desc_ar": "ذوبان ناعم يحاكي تأثير شريط الأفلام التناظرية الكلاسيكية",
        "desc_en": "Soft film-like dissolve blending both scenes smoothly",
        "default_duration": 0.5,
        "is_popular": True,
    },
    "fadegrays": {
        "key": "fadegrays",
        "label_ar": "تلاشي أحادي رمادي (Fade Grays)",
        "label_en": "Monochrome Gray Fade",
        "category": "fade",
        "icon": "🌫️",
        "desc_ar": "تلاشي نغمي رمادي هادئ ومحايد للمحتوى الوثائقي الهادئ",
        "desc_en": "Neutral monochrome gray fade for documentary pacing",
        "default_duration": 0.6,
        "is_popular": False,
    },
    "fadefast": {
        "key": "fadefast",
        "label_ar": "تلاشي سريع (Fast Fade)",
        "label_en": "Snappy Fast Fade",
        "category": "fade",
        "icon": "⏩",
        "desc_ar": "تلاشي سريع جداً ومناسب لإيقاع السوشيال ميديا وريلز تيك توك",
        "desc_en": "Ultra fast crossfade for high tempo fast cuts",
        "default_duration": 0.25,
        "is_popular": False,
    },
    "fadeslow": {
        "key": "fadeslow",
        "label_ar": "تلاشي بطيء حالم (Dreamy Slow Fade)",
        "label_en": "Dreamy Slow Fade",
        "category": "fade",
        "icon": "🌙",
        "desc_ar": "تلاشي شاعري طويل وبطيء للذكريات والمشاهد العاطفية",
        "desc_en": "Long atmospheric slow transition for emotional scenes",
        "default_duration": 1.0,
        "is_popular": False,
    },

    # ---------------- 2. Motion & Slides ----------------
    "smoothleft": {
        "key": "smoothleft",
        "label_ar": "انزلاق ناعم لليسار (Smooth Slide Left)",
        "label_en": "Smooth Slide Left",
        "category": "motion",
        "icon": "⬅️",
        "desc_ar": "حركة انسيابية فائقة النعومة تدفع الكادر لليسار (الأكثر طلباً)",
        "desc_en": "Ultra smooth push slide moving leftwards",
        "default_duration": 0.5,
        "is_popular": True,
    },
    "smoothright": {
        "key": "smoothright",
        "label_ar": "انزلاق ناعم لليمين (Smooth Slide Right)",
        "label_en": "Smooth Slide Right",
        "category": "motion",
        "icon": "➡️",
        "desc_ar": "حركة انسيابية ناعمة تدفع الكادر لليمين باتجاه القراءة العربي",
        "desc_en": "Ultra smooth push slide moving rightwards",
        "default_duration": 0.5,
        "is_popular": True,
    },
    "smoothup": {
        "key": "smoothup",
        "label_ar": "انزلاق ناعم للأعلى (Smooth Slide Up)",
        "label_en": "Smooth Slide Up",
        "category": "motion",
        "icon": "⬆️",
        "desc_ar": "حركة رفع ناعمة للأعلى مثالية للفيديوهات العمودية والشورتس",
        "desc_en": "Vertical smooth slide rising up, great for Shorts/Reels",
        "default_duration": 0.45,
        "is_popular": True,
    },
    "smoothdown": {
        "key": "smoothdown",
        "label_ar": "انزلاق ناعم للأسفل (Smooth Slide Down)",
        "label_en": "Smooth Slide Down",
        "category": "motion",
        "icon": "⬇️",
        "desc_ar": "حركة هبوط ناعمة وسلسة للكادر للأسفل",
        "desc_en": "Smooth vertical drop slide moving down",
        "default_duration": 0.45,
        "is_popular": False,
    },
    "slideleft": {
        "key": "slideleft",
        "label_ar": "دفع كلاسيكي لليسار (Push Left)",
        "label_en": "Push Slide Left",
        "category": "motion",
        "icon": "👈",
        "desc_ar": "دفع كلاسيكي مباشر للشاشة لليسار مثل كاب كات وبريميير",
        "desc_en": "Classic linear push slide to the left",
        "default_duration": 0.4,
        "is_popular": False,
    },
    "slideright": {
        "key": "slideright",
        "label_ar": "دفع كلاسيكي لليمين (Push Right)",
        "label_en": "Push Slide Right",
        "category": "motion",
        "icon": "👉",
        "desc_ar": "دفع كلاسيكي مباشر للشاشة لليمين",
        "desc_en": "Classic linear push slide to the right",
        "default_duration": 0.4,
        "is_popular": False,
    },
    "slideup": {
        "key": "slideup",
        "label_ar": "دفع كلاسيكي للأعلى (Push Up)",
        "label_en": "Push Slide Up",
        "category": "motion",
        "icon": "👆",
        "desc_ar": "دفع سريع للكادر للأعلى مثل سحب الشاشة بالهاتف",
        "desc_en": "Phone scroll up style push transition",
        "default_duration": 0.4,
        "is_popular": False,
    },
    "slidedown": {
        "key": "slidedown",
        "label_ar": "دفع كلاسيكي للأسفل (Push Down)",
        "label_en": "Push Slide Down",
        "category": "motion",
        "icon": "👇",
        "desc_ar": "دفع مباشر للكادر للأسفل",
        "desc_en": "Classic push slide moving downward",
        "default_duration": 0.4,
        "is_popular": False,
    },
    "coverleft": {
        "key": "coverleft",
        "label_ar": "تغطية من اليسار (Cover Left)",
        "label_en": "Cover from Left",
        "category": "motion",
        "icon": "📑",
        "desc_ar": "المشهد الجديد يدخل فوق المشهد السابق كأنه ورقة تغطيه",
        "desc_en": "New video layer slides over the previous frame",
        "default_duration": 0.5,
        "is_popular": False,
    },
    "coverright": {
        "key": "coverright",
        "label_ar": "تغطية من اليمين (Cover Right)",
        "label_en": "Cover from Right",
        "category": "motion",
        "icon": "📄",
        "desc_ar": "المشهد الجديد يغطي اللقطة السابقة قادماً من اليمين",
        "desc_en": "New video layer covers the old one from the right",
        "default_duration": 0.5,
        "is_popular": False,
    },
    "revealleft": {
        "key": "revealleft",
        "label_ar": "كشف لليسار (Reveal Left)",
        "label_en": "Reveal to Left",
        "category": "motion",
        "icon": "🪟",
        "desc_ar": "المشهد الحالي ينزلق كاشفاً المشهد الجديد الثابت خلفه",
        "desc_en": "Old frame slides away to reveal the new frame behind",
        "default_duration": 0.5,
        "is_popular": False,
    },
    "revealright": {
        "key": "revealright",
        "label_ar": "كشف لليمين (Reveal Right)",
        "label_en": "Reveal to Right",
        "category": "motion",
        "icon": "🚪",
        "desc_ar": "المشهد الحالي ينزلق لليمين كاشفاً اللقطة التالية وراءه",
        "desc_en": "Old frame slides to the right revealing next clip",
        "default_duration": 0.5,
        "is_popular": False,
    },

    # ---------------- 3. Zooms & Optics ----------------
    "zoomin": {
        "key": "zoomin",
        "label_ar": "تكبير ديناميكي حركي (Dynamic Zoom In)",
        "label_en": "Dynamic Zoom In",
        "category": "zoom",
        "icon": "🔍",
        "desc_ar": "زوم سريع يكبر الكادر للداخل بانتقال حركي عصري وجذاب",
        "desc_en": "High energy camera zoom-in transition",
        "default_duration": 0.45,
        "is_popular": True,
    },
    "circlecrop": {
        "key": "circlecrop",
        "label_ar": "دائرة قناع سينمائي (Iris Circle Crop)",
        "label_en": "Iris Circle Crop",
        "category": "zoom",
        "icon": "🎯",
        "desc_ar": "دائرة كلاسيكية تضيق على المتحدث ثم تفتح على المشهد الجديد",
        "desc_en": "Classic cinema iris circle transition",
        "default_duration": 0.6,
        "is_popular": True,
    },
    "circleopen": {
        "key": "circleopen",
        "label_ar": "انفتاح دائري ناعم (Circle Open)",
        "label_en": "Circle Iris Open",
        "category": "zoom",
        "icon": "🔘",
        "desc_ar": "دائرة تنفتح من المنتصف لتكشف اللقطة الجديدة بأسلوب فخم",
        "desc_en": "Expanding circle from center revealing new clip",
        "default_duration": 0.55,
        "is_popular": True,
    },
    "circleclose": {
        "key": "circleclose",
        "label_ar": "انغلاق دائري (Circle Close)",
        "label_en": "Circle Iris Close",
        "category": "zoom",
        "icon": "⚫",
        "desc_ar": "دائرة تنغلق نحو المركز لتركيز الانتباه قبل الانتقال",
        "desc_en": "Contracting circle closing onto center",
        "default_duration": 0.55,
        "is_popular": False,
    },
    "rectcrop": {
        "key": "rectcrop",
        "label_ar": "إطار مستطيل متدرج (Rect Crop)",
        "label_en": "Rectangular Frame Crop",
        "category": "zoom",
        "icon": "🔲",
        "desc_ar": "قناع مستطيل أنيق يفتح الكادر من المركز للخارج",
        "desc_en": "Expanding rectangular frame reveal",
        "default_duration": 0.5,
        "is_popular": False,
    },
    "distance": {
        "key": "distance",
        "label_ar": "انتقال بعد بصري (Optical Distance)",
        "label_en": "Optical Distance",
        "category": "zoom",
        "icon": "🌌",
        "desc_ar": "تأثير بصري يبتعد في العمق الثلاثي الأبعاد ثم يقترب",
        "desc_en": "3D optical depth distance transition",
        "default_duration": 0.6,
        "is_popular": False,
    },
    "hblur": {
        "key": "hblur",
        "label_ar": "تمويه حركة أفقي (Motion Blur Pan)",
        "label_en": "Horizontal Motion Blur",
        "category": "zoom",
        "icon": "💨",
        "desc_ar": "تمويه حركة جانبي يمنح شعور حركة كاميرا سينمائية سريعة",
        "desc_en": "Cinematic whip pan with horizontal motion blur",
        "default_duration": 0.35,
        "is_popular": True,
    },

    # ---------------- 4. Wipes & Slices ----------------
    "wipeleft": {
        "key": "wipeleft",
        "label_ar": "مسح ناعم لليسار (Wipe Left)",
        "label_en": "Soft Wipe Left",
        "category": "wipe",
        "icon": "🧹",
        "desc_ar": "مسح تدريجي أفقي ناعم يمسح الشاشة من اليمين لليسار",
        "desc_en": "Linear soft wipe moving across to the left",
        "default_duration": 0.5,
        "is_popular": True,
    },
    "wiperight": {
        "key": "wiperight",
        "label_ar": "مسح ناعم لليمين (Wipe Right)",
        "label_en": "Soft Wipe Right",
        "category": "wipe",
        "icon": "🖌️",
        "desc_ar": "مسح تدريجي أفقي يمسح الشاشة من اليسار لليمين",
        "desc_en": "Linear soft wipe moving across to the right",
        "default_duration": 0.5,
        "is_popular": True,
    },
    "wipeup": {
        "key": "wipeup",
        "label_ar": "مسح ناعم للأعلى (Wipe Up)",
        "label_en": "Soft Wipe Up",
        "category": "wipe",
        "icon": "🔼",
        "desc_ar": "مسح رأسي يرتفع من أسفل الشاشة لأعلاها بنقاء",
        "desc_en": "Vertical wipe rising from bottom to top",
        "default_duration": 0.45,
        "is_popular": False,
    },
    "wipedown": {
        "key": "wipedown",
        "label_ar": "مسح ناعم للأسفل (Wipe Down)",
        "label_en": "Soft Wipe Down",
        "category": "wipe",
        "icon": "🔽",
        "desc_ar": "مسح رأسي يهبط من أعلى الشاشة لأسفلها",
        "desc_en": "Vertical wipe descending from top to bottom",
        "default_duration": 0.45,
        "is_popular": False,
    },
    "horzopen": {
        "key": "horzopen",
        "label_ar": "ستارة أفقية مفتوحة (Horz Curtain Open)",
        "label_en": "Horizontal Curtain Open",
        "category": "wipe",
        "icon": "↔️",
        "desc_ar": "ستارة مسرح تنفتح أفقياً من المركز نحو الحواف",
        "desc_en": "Stage curtain opening horizontally from center",
        "default_duration": 0.6,
        "is_popular": True,
    },
    "horzclose": {
        "key": "horzclose",
        "label_ar": "ستارة أفقية مغلقة (Horz Curtain Close)",
        "label_en": "Horizontal Curtain Close",
        "category": "wipe",
        "icon": "🚪",
        "desc_ar": "ستارة أفقية تنغلق من الحواف نحو مركز الشاشة",
        "desc_en": "Curtain closing horizontally towards center",
        "default_duration": 0.6,
        "is_popular": False,
    },
    "vertopen": {
        "key": "vertopen",
        "label_ar": "ستارة رأسية مفتوحة (Vert Curtain Open)",
        "label_en": "Vertical Curtain Open",
        "category": "wipe",
        "icon": "↕️",
        "desc_ar": "ستارة رأسية تنفتح للأعلى والأسفل معاً كاشفة الفيديو",
        "desc_en": "Vertical split opening upwards and downwards",
        "default_duration": 0.6,
        "is_popular": False,
    },
    "vertclose": {
        "key": "vertclose",
        "label_ar": "ستارة رأسية مغلقة (Vert Curtain Close)",
        "label_en": "Vertical Curtain Close",
        "category": "wipe",
        "icon": "📦",
        "desc_ar": "ستارة رأسية تنغلق من الأعلى والأسفل نحو المنتصف",
        "desc_en": "Vertical split closing towards the center line",
        "default_duration": 0.6,
        "is_popular": False,
    },
    "radial": {
        "key": "radial",
        "label_ar": "مسح دائري كعقارب الساعة (Radial Clockwise)",
        "label_en": "Radial Clockwise Wipe",
        "category": "wipe",
        "icon": "⏱️",
        "desc_ar": "مسح دائري بزاوية 360 درجة يحاكي حركة عقارب الساعة الكلاسيكية",
        "desc_en": "360 degree radial clock sweep transition",
        "default_duration": 0.6,
        "is_popular": False,
    },
    "hlslice": {
        "key": "hlslice",
        "label_ar": "شرائح أفقية متحركة (Horizontal Slices)",
        "label_en": "Horizontal Slices",
        "category": "wipe",
        "icon": "📊",
        "desc_ar": "تقطيع الشاشة لشرائح أفقية متداخلة تتحرك بأسلوب تلفزيوني",
        "desc_en": "Interlaced horizontal slice wipe",
        "default_duration": 0.5,
        "is_popular": False,
    },
    "vuslice": {
        "key": "vuslice",
        "label_ar": "شرائح رأسية للأعلى (Vertical Slices)",
        "label_en": "Vertical Slices",
        "category": "wipe",
        "icon": "📉",
        "desc_ar": "تقطيع الشاشة لأعمدة رأسية ترتفع بتتابع متناسق",
        "desc_en": "Vertical columns rising in alternating sequence",
        "default_duration": 0.5,
        "is_popular": False,
    },
    "diagtl": {
        "key": "diagtl",
        "label_ar": "مسح قطري علوي (Diagonal Top-Left)",
        "label_en": "Diagonal Wipe Top-Left",
        "category": "wipe",
        "icon": "📐",
        "desc_ar": "مسح قطري هندسي يبدأ بزاوية 45 درجة من أعلى اليسار",
        "desc_en": "45 degree diagonal wipe from top-left",
        "default_duration": 0.5,
        "is_popular": False,
    },
    "diagbr": {
        "key": "diagbr",
        "label_ar": "مسح قطري سفلي (Diagonal Bottom-Right)",
        "label_en": "Diagonal Wipe Bottom-Right",
        "category": "wipe",
        "icon": "📐",
        "desc_ar": "مسح قطري مائل يبدأ من أسفل اليمين نحو الأعلى",
        "desc_en": "45 degree diagonal wipe from bottom-right",
        "default_duration": 0.5,
        "is_popular": False,
    },

    # ---------------- 5. Trendy & Social ----------------
    "pixelize": {
        "key": "pixelize",
        "label_ar": "بيكسيل وموزاييك رقمي (Digital Pixelize)",
        "label_en": "Digital Pixelize Glitch",
        "category": "trendy",
        "icon": "👾",
        "desc_ar": "تأثير غليتش بكسلي عصري ومحبوب جداً لفيديوهات التقنية والجيمنج",
        "desc_en": "Digital mosaic pixelate glitch effect, ideal for tech & gaming",
        "default_duration": 0.4,
        "is_popular": True,
    },
    "squeezeh": {
        "key": "squeezeh",
        "label_ar": "ضغط سينمائي أفقي (Squeeze Horizontal)",
        "label_en": "Squeeze Horizontal",
        "category": "trendy",
        "icon": "🗜️",
        "desc_ar": "ضغط مرن للمشهد القديم أفقياً ليفسح المجال للمشهد القادم",
        "desc_en": "Horizontal elastic squeeze transition",
        "default_duration": 0.45,
        "is_popular": False,
    },
    "squeezev": {
        "key": "squeezev",
        "label_ar": "ضغط سينمائي رأسي (Squeeze Vertical)",
        "label_en": "Squeeze Vertical",
        "category": "trendy",
        "icon": "🔽",
        "desc_ar": "ضغط رأسي مرن للكادر يجعله يبدو كشريط يقفز للقطة التالية",
        "desc_en": "Vertical elastic squeeze transition",
        "default_duration": 0.45,
        "is_popular": False,
    },
    "hlwind": {
        "key": "hlwind",
        "label_ar": "عاصفة ريح أفقية (Wind Sweep Left)",
        "label_en": "Wind Sweep Left",
        "category": "trendy",
        "icon": "🌪️",
        "desc_ar": "تأثير خطوط هوائية سريعة تعصف بالكادر نحو اليسار",
        "desc_en": "Dynamic wind streak sweep to the left",
        "default_duration": 0.4,
        "is_popular": False,
    },
    "hrwind": {
        "key": "hrwind",
        "label_ar": "عاصفة ريح لليمين (Wind Sweep Right)",
        "label_en": "Wind Sweep Right",
        "category": "trendy",
        "icon": "💨",
        "desc_ar": "تأثير خطوط ريح سريعة تدفع الكادر لليمين بطاقة عالية",
        "desc_en": "Dynamic wind streak sweep to the right",
        "default_duration": 0.4,
        "is_popular": False,
    },
    "vuwind": {
        "key": "vuwind",
        "label_ar": "عاصفة ريح للأعلى (Wind Sweep Up)",
        "label_en": "Wind Sweep Up",
        "category": "trendy",
        "icon": "🚀",
        "desc_ar": "عاصفة ريح تصاعدية ترفع الكادر للأعلى بإثارة",
        "desc_en": "Upward wind streak transition",
        "default_duration": 0.4,
        "is_popular": False,
    },
    "vdwind": {
        "key": "vdwind",
        "label_ar": "عاصفة ريح للأسفل (Wind Sweep Down)",
        "label_en": "Wind Sweep Down",
        "category": "trendy",
        "icon": "🌊",
        "desc_ar": "عاصفة ريح هابطة تدفع الكادر للأسفل",
        "desc_en": "Downward wind streak transition",
        "default_duration": 0.4,
        "is_popular": False,
    },
}


def get_transition_info(key: str) -> Dict[str, Any]:
    """Retrieves metadata dict for a transition key with safe fallback to crossfade."""
    if key in TRANSITION_PRESETS:
        return TRANSITION_PRESETS[key]
    return TRANSITION_PRESETS["smoothleft"]


def list_transitions_by_category(cat: str = "all") -> List[Dict[str, Any]]:
    """Returns sorted list of transition presets filtered by category."""
    if not cat or cat == "all":
        # Put popular items first, then alphabetical
        return sorted(
            TRANSITION_PRESETS.values(),
            key=lambda x: (not x.get("is_popular", False), x.get("category", ""), x.get("key", ""))
        )
    return [p for p in TRANSITION_PRESETS.values() if p.get("category") == cat]


def render_simulated_transition_frame(
    img_a: Image.Image,
    img_b: Image.Image,
    trans_key: str,
    progress: float,
) -> Image.Image:
    """
    Simulates a transition frame between img_a (outgoing) and img_b (incoming)
    at progress t in [0.0, 1.0]. Used for zero-lag live interactive GUI animation.
    """
    t = max(0.0, min(1.0, float(progress)))
    if t <= 0.001:
        return img_a
    if t >= 0.999:
        return img_b

    w, h = img_a.size
    if img_b.size != (w, h):
        img_b = img_b.resize((w, h), Image.Resampling.BILINEAR)

    # 1. Fade / Crossfade
    if trans_key in ("fade", "dissolve", "fadefast", "fadeslow"):
        return Image.blend(img_a, img_b, t)

    # 2. Dip to Black
    if trans_key == "fadeblack":
        black = Image.new("RGB", (w, h), (0, 0, 0))
        if t < 0.5:
            alpha = t * 2.0
            return Image.blend(img_a, black, alpha)
        else:
            alpha = (t - 0.5) * 2.0
            return Image.blend(black, img_b, alpha)

    # 3. Flash to White
    if trans_key == "fadewhite":
        white = Image.new("RGB", (w, h), (255, 255, 255))
        if t < 0.5:
            alpha = t * 2.0
            return Image.blend(img_a, white, alpha)
        else:
            alpha = (t - 0.5) * 2.0
            return Image.blend(white, img_b, alpha)

    # 4. Slide Left (Push)
    if trans_key in ("smoothleft", "slideleft", "hlwind"):
        out = Image.new("RGB", (w, h))
        shift_x = int(t * w)
        out.paste(img_a, (-shift_x, 0))
        out.paste(img_b, (w - shift_x, 0))
        return out

    # 5. Slide Right
    if trans_key in ("smoothright", "slideright", "hrwind"):
        out = Image.new("RGB", (w, h))
        shift_x = int(t * w)
        out.paste(img_a, (shift_x, 0))
        out.paste(img_b, (-w + shift_x, 0))
        return out

    # 6. Slide Up
    if trans_key in ("smoothup", "slideup", "vuwind"):
        out = Image.new("RGB", (w, h))
        shift_y = int(t * h)
        out.paste(img_a, (0, -shift_y))
        out.paste(img_b, (0, h - shift_y))
        return out

    # 7. Slide Down
    if trans_key in ("smoothdown", "slidedown", "vdwind"):
        out = Image.new("RGB", (w, h))
        shift_y = int(t * h)
        out.paste(img_a, (0, shift_y))
        out.paste(img_b, (0, -h + shift_y))
        return out

    # 8. Cover Left
    if trans_key == "coverleft":
        out = img_a.copy()
        shift_x = int((1.0 - t) * w)
        out.paste(img_b, (shift_x, 0))
        return out

    # 9. Cover Right
    if trans_key == "coverright":
        out = img_a.copy()
        shift_x = int((t - 1.0) * w)
        out.paste(img_b, (shift_x, 0))
        return out

    # 10. Reveal Left
    if trans_key == "revealleft":
        out = img_b.copy()
        shift_x = int(t * w)
        out.paste(img_a, (-shift_x, 0))
        return out

    # 11. Reveal Right
    if trans_key == "revealright":
        out = img_b.copy()
        shift_x = int(t * w)
        out.paste(img_a, (shift_x, 0))
        return out

    # 12. Wipe Left
    if trans_key == "wipeleft":
        split_x = int((1.0 - t) * w)
        out = img_b.copy()
        crop_a = img_a.crop((0, 0, split_x, h))
        out.paste(crop_a, (0, 0))
        return out

    # 13. Wipe Right
    if trans_key == "wiperight":
        split_x = int(t * w)
        out = img_a.copy()
        crop_b = img_b.crop((0, 0, split_x, h))
        out.paste(crop_b, (0, 0))
        return out

    # 14. Wipe Up
    if trans_key == "wipeup":
        split_y = int((1.0 - t) * h)
        out = img_b.copy()
        crop_a = img_a.crop((0, 0, w, split_y))
        out.paste(crop_a, (0, 0))
        return out

    # 15. Wipe Down
    if trans_key == "wipedown":
        split_y = int(t * h)
        out = img_a.copy()
        crop_b = img_b.crop((0, 0, w, split_y))
        out.paste(crop_b, (0, 0))
        return out

    # 16. Curtain Open (Horz)
    if trans_key == "horzopen":
        open_w = int((t * w) / 2.0)
        out = img_a.copy()
        mid_x = w // 2
        crop_b_mid = img_b.crop((mid_x - open_w, 0, mid_x + open_w, h))
        out.paste(crop_b_mid, (mid_x - open_w, 0))
        return out

    # 17. Curtain Open (Vert)
    if trans_key == "vertopen":
        open_h = int((t * h) / 2.0)
        out = img_a.copy()
        mid_y = h // 2
        crop_b_mid = img_b.crop((0, mid_y - open_h, w, mid_y + open_h))
        out.paste(crop_b_mid, (0, mid_y - open_h))
        return out

    # 18. Zoom In
    if trans_key == "zoomin":
        scale = 0.2 + (0.8 * t)
        nw, nh = max(4, int(w * scale)), max(4, int(h * scale))
        scaled_b = img_b.resize((nw, nh), Image.Resampling.BILINEAR)
        out = Image.blend(img_a, img_b, t * 0.7)
        px = (w - nw) // 2
        py = (h - nh) // 2
        out.paste(scaled_b, (px, py))
        return out

    # 19. Circle Open
    if trans_key in ("circleopen", "circlecrop"):
        max_r = math.hypot(w, h) / 2.0
        r = max(1.0, t * max_r)
        mask = Image.new("L", (w, h), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        cx, cy = w // 2, h // 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        out = img_a.copy()
        out.paste(img_b, (0, 0), mask)
        return out

    # 20. Pixelize
    if trans_key == "pixelize":
        block_factor = max(1, int(math.sin(t * math.pi) * 24.0))
        if block_factor <= 1:
            return Image.blend(img_a, img_b, t)
        small_a = img_a.resize((w // block_factor, h // block_factor), Image.Resampling.NEAREST)
        small_b = img_b.resize((w // block_factor, h // block_factor), Image.Resampling.NEAREST)
        pix_a = small_a.resize((w, h), Image.Resampling.NEAREST)
        pix_b = small_b.resize((w, h), Image.Resampling.NEAREST)
        return Image.blend(pix_a, pix_b, t)

    # Fallback to smooth blend
    return Image.blend(img_a, img_b, t)


def build_xfade_filter_chains(
    n_segs: int,
    seg_durations: List[float],
    transitions_config: Optional[Dict[str, Any]] = None,
    has_audio: bool = True,
    v_seg_prefix: str = "v_seg_",
    a_seg_prefix: str = "a_seg_",
    v_out_label: str = "v_tl_base",
    a_out_label: str = "a_tl_base",
) -> Tuple[List[str], float]:
    """
    Constructs the exact, verified FFmpeg filter chains for chaining N video segments
    using `xfade` (video transitions) and `acrossfade` (audio crossfade).
    Supports:
    - Selective transitions on specific cuts (with hard cuts on other seams).
    - Global transitions applied to all cuts.
    - Automatic grouping of segments connected by hard cuts for optimal FFmpeg performance.
    Returns (chains_list, total_resulting_duration).
    """
    if n_segs <= 0:
        return [], 0.0

    if n_segs == 1:
        chains = [f"[{v_seg_prefix}0]null[{v_out_label}]"]
        if has_audio:
            chains.append(f"[{a_seg_prefix}0]anull[{a_out_label}]")
        return chains, seg_durations[0] if seg_durations else 0.0

    cfg = transitions_config or {}
    enabled = bool(cfg.get("enabled", False))
    def_trans = cfg.get("default_transition", "smoothleft")
    def_dur = float(cfg.get("default_duration", 0.5))
    do_acrossfade = bool(cfg.get("audio_crossfade", True))
    apply_to_all = bool(cfg.get("apply_to_all", True))
    clip_trans_map = cfg.get("clip_transitions", {})

    # Determine transition for each cut: cut k is between seg k and seg k+1
    # cut index ranges from 0 to n_segs - 2
    cuts_info: List[Tuple[Optional[str], float]] = []
    any_active_trans = False

    for k in range(n_segs - 1):
        cut_override = clip_trans_map.get(str(k), clip_trans_map.get(k, None))
        if cut_override is not None:
            if isinstance(cut_override, str):
                t_key = cut_override
                t_dur = def_dur
            elif isinstance(cut_override, dict):
                t_key = cut_override.get("transition", def_trans)
                t_dur = float(cut_override.get("duration", def_dur))
            else:
                t_key = def_trans
                t_dur = def_dur
        elif apply_to_all and enabled and def_trans not in ("none", "", None):
            t_key = def_trans
            t_dur = def_dur
        else:
            t_key = "none"
            t_dur = 0.0

        if not enabled or t_key in ("none", "", None):
            cuts_info.append((None, 0.0))
        else:
            if t_key not in TRANSITION_PRESETS:
                t_key = "smoothleft"
            cuts_info.append((t_key, t_dur))
            any_active_trans = True

    # If no transitions are active, use fast single-pass concat
    if not any_active_trans:
        v_inputs = "".join(f"[{v_seg_prefix}{i}]" for i in range(n_segs))
        chains = []
        if has_audio:
            a_inputs = "".join(f"[{a_seg_prefix}{i}]" for i in range(n_segs))
            chains.append(f"{v_inputs}{a_inputs}concat=n={n_segs}:v=1:a=1[{v_out_label}][{a_out_label}]")
        else:
            chains.append(f"{v_inputs}concat=n={n_segs}:v=1:a=0[{v_out_label}]")
        return chains, sum(seg_durations)

    # Group segments separated by active transitions
    # groups: list of segment index lists
    groups: List[List[int]] = []
    curr_group: List[int] = [0]
    group_transitions: List[Tuple[str, float]] = []

    for k in range(n_segs - 1):
        trans, dur = cuts_info[k]
        if trans is not None:
            groups.append(curr_group)
            group_transitions.append((trans, dur))
            curr_group = [k + 1]
        else:
            curr_group.append(k + 1)
    groups.append(curr_group)

    chains = []
    n_groups = len(groups)
    grp_v_labels: List[str] = []
    grp_a_labels: List[str] = []
    grp_durations: List[float] = []

    for g_idx, grp_segs in enumerate(groups):
        grp_dur = sum(seg_durations[s] for s in grp_segs)
        grp_durations.append(grp_dur)
        if len(grp_segs) == 1:
            s_idx = grp_segs[0]
            grp_v_labels.append(f"{v_seg_prefix}{s_idx}")
            grp_a_labels.append(f"{a_seg_prefix}{s_idx}")
        else:
            out_v = f"v_grp_{g_idx}"
            out_a = f"a_grp_{g_idx}"
            v_in = "".join(f"[{v_seg_prefix}{s}]" for s in grp_segs)
            if has_audio:
                a_in = "".join(f"[{a_seg_prefix}{s}]" for s in grp_segs)
                chains.append(f"{v_in}{a_in}concat=n={len(grp_segs)}:v=1:a=1[{out_v}][out_a={out_a}]" if False else f"{v_in}{a_in}concat=n={len(grp_segs)}:v=1:a=1[{out_v}][{out_a}]")
            else:
                chains.append(f"{v_in}concat=n={len(grp_segs)}:v=1:a=0[{out_v}]")
            grp_v_labels.append(out_v)
            grp_a_labels.append(out_a)

    # Chain groups with xfade
    cur_v = f"[{grp_v_labels[0]}]"
    cur_a = f"[{grp_a_labels[0]}]" if has_audio else None
    accum_dur = max(0.08, grp_durations[0])

    for j in range(1, n_groups):
        g_dur = max(0.08, grp_durations[j])
        t_key, t_dur = group_transitions[j - 1]

        # Safe clamp: duration cannot exceed 45% of either incoming accumulated or next group
        max_allowed_dur = min(accum_dur * 0.45, g_dur * 0.45)
        eff_dur = max(0.05, min(t_dur, max_allowed_dur))
        offset = max(0.0, accum_dur - eff_dur)

        next_v = f"v_xfade_{j}"
        next_v_label = v_out_label if j == n_groups - 1 else next_v

        chains.append(
            f"{cur_v}[{grp_v_labels[j]}]xfade=transition={t_key}:duration={eff_dur:.3f}:offset={offset:.3f}[{next_v_label}]"
        )
        cur_v = f"[{next_v}]"

        if has_audio:
            next_a = f"a_xfade_{j}"
            next_a_label = a_out_label if j == n_groups - 1 else next_a
            if do_acrossfade:
                chains.append(
                    f"{cur_a}[{grp_a_labels[j]}]acrossfade=d={eff_dur:.3f}:c1=tri:c2=tri[{next_a_label}]"
                )
            else:
                chains.append(
                    f"{cur_a}[{grp_a_labels[j]}]concat=n=2:v=0:a=1[{next_a_label}]"
                )
            cur_a = f"[{next_a}]"

        accum_dur = accum_dur + g_dur - eff_dur

    return chains, accum_dur
