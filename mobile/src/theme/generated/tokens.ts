// Generated from 00-docs/15-design/design/design-tokens.json by `make gen` - DO NOT EDIT.
// Design tokens version 1.0.0.

export const designTokens = {
  "color": {
    "dark": {
      "brand": {
        "primary": "#FFB547",
        "onPrimary": "#15111C",
        "primaryText": "#FFB547",
        "primaryContainer": "rgba(255,181,71,0.13)",
        "secondary": "#FF6B8B",
        "onSecondary": "#15111C",
        "secondaryText": "#FF6B8B",
        "secondaryContainer": "rgba(255,107,139,0.14)"
      },
      "status": {
        "error": "#FF6B8B",
        "onError": "#15111C",
        "errorContainer": "rgba(255,107,139,0.14)",
        "warning": "#FFA24C",
        "onWarning": "#15111C",
        "warningContainer": "rgba(255,162,76,0.14)",
        "success": "#7ED957",
        "onSuccess": "#15111C",
        "successContainer": "rgba(126,217,87,0.14)",
        "info": "#60A5FA",
        "onInfo": "#15111C"
      },
      "moderator": {
        "primary": "#2DD4BF",
        "onPrimary": "#062321",
        "text": "#5EEAD4",
        "banner": "#0E3B38",
        "container": "rgba(45,212,191,0.14)"
      },
      "surface": {
        "background": "#15111C",
        "surface": "#231C30",
        "surfaceVariant": "#2A2335",
        "sheet": "#1D1727",
        "drawer": "#1B1624",
        "floating": "rgba(35,28,48,0.94)",
        "glass": "rgba(21,17,28,0.72)",
        "onSurface": "#F4EEF8",
        "onSurfaceMuted": "#A89BB8",
        "onSurfaceFaint": "#6E6380",
        "outline": "rgba(255,255,255,0.09)",
        "scrim": "rgba(8,5,12,0.6)",
        "skeleton": "#2E2639",
        "placeholderA": "#2C2438",
        "placeholderB": "#261F31"
      }
    },
    "light": {
      "brand": {
        "primary": "#FFB547",
        "onPrimary": "#15111C",
        "primaryText": "#A35A00",
        "primaryContainer": "#FFF1DC",
        "secondary": "#FF6B8B",
        "onSecondary": "#15111C",
        "secondaryText": "#C8284F",
        "secondaryContainer": "#FFE4EA"
      },
      "status": {
        "error": "#C8284F",
        "onError": "#FFFFFF",
        "errorContainer": "#FFE4EA",
        "warning": "#B45309",
        "onWarning": "#FFFFFF",
        "warningContainer": "#FFEDD5",
        "success": "#2F7D32",
        "onSuccess": "#FFFFFF",
        "successContainer": "#E3F5DC",
        "info": "#2563EB",
        "onInfo": "#FFFFFF"
      },
      "moderator": {
        "primary": "#0F766E",
        "onPrimary": "#FFFFFF",
        "text": "#0F766E",
        "banner": "#CCFBF1",
        "container": "#DDF7F2"
      },
      "surface": {
        "background": "#FBF8F4",
        "surface": "#FFFFFF",
        "surfaceVariant": "#F1EBF3",
        "sheet": "#FFFFFF",
        "drawer": "#FFFFFF",
        "floating": "rgba(255,255,255,0.96)",
        "glass": "rgba(255,255,255,0.88)",
        "onSurface": "#231A2E",
        "onSurfaceMuted": "#6F6480",
        "onSurfaceFaint": "#A79DB3",
        "outline": "rgba(35,26,46,0.1)",
        "scrim": "rgba(20,12,28,0.4)",
        "skeleton": "#EDE6EF",
        "placeholderA": "#EFE6F0",
        "placeholderB": "#E8DDEA"
      }
    },
    "category": {
      "stadtfest": "#FFB547",
      "volksfest": "#FF6B8B",
      "weihnachtsmarkt": "#5EEAD4",
      "markt": "#8B9CFF",
      "palette5": "#7ED957",
      "palette6": "#C792EA"
    },
    "friend": {
      "blue": "#5B7FD6",
      "pink": "#C8508A",
      "green": "#3E9A84",
      "ochre": "#B07A2E",
      "violet": "#7B62D0",
      "rust": "#C85A3E"
    }
  },
  "font": {
    "display": "Young Serif",
    "ui": "Outfit"
  },
  "radius": {
    "phone": 44,
    "sheet": 28,
    "card": 22,
    "block": 20,
    "buttonLarge": 18,
    "button": 16,
    "input": 14,
    "chip": 12,
    "pill": 10
  },
  "motion": {
    "page": {
      "duration": 340,
      "easing": "cubic-bezier(.2,.8,.2,1)"
    },
    "sheet": {
      "duration": 340
    },
    "login": {
      "duration": 380
    },
    "toast": {
      "duration": 250,
      "visible": 2200
    }
  }
} as const;
