/* @ds-bundle: {"format":4,"namespace":"ReportKitchenDesignSystem_07c3a7","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Eyebrow","sourcePath":"components/core/Eyebrow.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"Link","sourcePath":"components/core/Link.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Textarea","sourcePath":"components/forms/Textarea.jsx"},{"name":"Accordion","sourcePath":"components/layout/Accordion.jsx"},{"name":"Callout","sourcePath":"components/layout/Callout.jsx"},{"name":"Card","sourcePath":"components/layout/Card.jsx"},{"name":"FeatureCard","sourcePath":"components/layout/FeatureCard.jsx"},{"name":"SectionHeading","sourcePath":"components/layout/SectionHeading.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"48c2f3d46c2b","components/core/Button.jsx":"0736194b2dbd","components/core/Eyebrow.jsx":"f64b61d406ec","components/core/Icon.jsx":"f508f561a134","components/core/Link.jsx":"904b9b8f7493","components/core/Tag.jsx":"076ae6018a34","components/forms/Input.jsx":"b074c92b08e8","components/forms/Select.jsx":"7ef41e2b147a","components/forms/Textarea.jsx":"8788c528fe68","components/layout/Accordion.jsx":"f2bbf1119ff5","components/layout/Callout.jsx":"c7c4e79db0ab","components/layout/Card.jsx":"73e89baf9351","components/layout/FeatureCard.jsx":"bb4fdf1e2b0e","components/layout/SectionHeading.jsx":"b1459ecf36e0","ui_kits/website/About.jsx":"10d602764f75","ui_kits/website/Header.jsx":"fa12d233a10e","ui_kits/website/Home.jsx":"6c2dcebdb5ad","ui_kits/website/Insights.jsx":"028606b35e9c","ui_kits/website/OfferingCustom.jsx":"39e93cb7ce8a","ui_kits/website/OurWork.jsx":"8db61219d31b","ui_kits/website/PatternLibrary.jsx":"51b6d205095b","ui_kits/website/ProjectProfile.jsx":"46873d217c60"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.ReportKitchenDesignSystem_07c3a7 = window.ReportKitchenDesignSystem_07c3a7 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
/**
 * Status Badge — small label for availability states used across offerings:
 * "Available now" (success), "Coming soon" (macaroni), "Free" / "New".
 */
function Badge({
  children,
  tone = "neutral",
  dot = false,
  style,
  ...rest
}) {
  const tones = {
    neutral: {
      bg: "var(--rk-gray-100)",
      fg: "var(--rk-rhino-700)",
      dot: "var(--rk-rhino-500)"
    },
    success: {
      bg: "rgba(46,139,87,0.12)",
      fg: "#1F6B41",
      dot: "var(--rk-success)"
    },
    soon: {
      bg: "var(--rk-macaroni-100)",
      fg: "var(--rk-macaroni-600)",
      dot: "var(--rk-macaroni-500)"
    },
    brand: {
      bg: "var(--rk-tomato-100)",
      fg: "var(--rk-tomato-700)",
      dot: "var(--rk-tomato-500)"
    }
  };
  const t = tones[tone] || tones.neutral;
  return React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: "0.06em",
      padding: "5px 10px",
      borderRadius: "var(--rk-radius-xs)",
      background: t.bg,
      color: t.fg,
      ...style
    },
    ...rest
  }, [dot ? React.createElement("span", {
    key: "d",
    style: {
      width: 7,
      height: 7,
      borderRadius: "50%",
      background: t.dot,
      display: "inline-block"
    }
  }) : null, React.createElement("span", {
    key: "t"
  }, children)]);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
/**
 * Report Kitchen primary action control.
 * Variants: primary (tomato), secondary (rhino outline), accent (macaroni),
 * ghost. Sizes sm | md | lg. Optional Lucide icon name on either side.
 */
function Button({
  children,
  variant = "primary",
  size = "md",
  pill = false,
  iconLeft,
  iconRight,
  href,
  disabled = false,
  full = false,
  style,
  ...rest
}) {
  const iconRef = React.useRef(null);
  React.useEffect(() => {
    if (window.lucide && iconRef.current) window.lucide.createIcons();
  });
  const sizes = {
    sm: {
      fontSize: 14,
      padding: "8px 16px",
      gap: 6,
      icon: 16
    },
    md: {
      fontSize: 16,
      padding: "12px 22px",
      gap: 8,
      icon: 18
    },
    lg: {
      fontSize: 18,
      padding: "16px 30px",
      gap: 10,
      icon: 20
    }
  };
  const s = sizes[size] || sizes.md;
  const palette = {
    primary: {
      bg: "var(--rk-tomato-500)",
      bgHover: "var(--rk-tomato-600)",
      fg: "#fff",
      bd: "transparent"
    },
    secondary: {
      bg: "transparent",
      bgHover: "var(--rk-rhino-100)",
      fg: "var(--rk-rhino-700)",
      bd: "var(--rk-rhino-700)"
    },
    accent: {
      bg: "var(--rk-macaroni-500)",
      bgHover: "var(--rk-macaroni-600)",
      fg: "var(--rk-rhino-900)",
      bd: "transparent"
    },
    ghost: {
      bg: "transparent",
      bgHover: "var(--rk-rhino-100)",
      fg: "var(--rk-rhino-700)",
      bd: "transparent"
    }
  };
  const p = palette[variant] || palette.primary;
  const base = {
    display: full ? "flex" : "inline-flex",
    width: full ? "100%" : undefined,
    alignItems: "center",
    justifyContent: "center",
    gap: s.gap,
    fontFamily: "var(--rk-font-body)",
    fontWeight: 700,
    fontSize: s.fontSize,
    lineHeight: 1,
    padding: s.padding,
    color: p.fg,
    background: p.bg,
    border: `2px solid ${p.bd}`,
    borderRadius: pill ? "var(--rk-radius-pill)" : "var(--rk-radius-sm)",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    textDecoration: "none",
    transition: "background var(--rk-dur) var(--rk-ease-out), transform var(--rk-dur-fast) var(--rk-ease-out), box-shadow var(--rk-dur) var(--rk-ease-out)",
    whiteSpace: "nowrap",
    ...style
  };
  const onEnter = e => {
    if (disabled) return;
    e.currentTarget.style.background = p.bgHover;
    e.currentTarget.style.transform = "translateY(-1px)";
  };
  const onLeave = e => {
    if (disabled) return;
    e.currentTarget.style.background = p.bg;
    e.currentTarget.style.transform = "translateY(0)";
  };
  const inner = [iconLeft ? React.createElement("i", {
    key: "l",
    ref: iconRef,
    "data-lucide": iconLeft,
    width: s.icon,
    height: s.icon,
    style: {
      strokeWidth: 2.25
    }
  }) : null, React.createElement("span", {
    key: "t"
  }, children), iconRight ? React.createElement("i", {
    key: "r",
    ref: iconRef,
    "data-lucide": iconRight,
    width: s.icon,
    height: s.icon,
    style: {
      strokeWidth: 2.25
    }
  }) : null];
  const tag = href ? "a" : "button";
  return React.createElement(tag, {
    style: base,
    href: href,
    disabled: tag === "button" ? disabled : undefined,
    onMouseEnter: onEnter,
    onMouseLeave: onLeave,
    ...rest
  }, inner);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Eyebrow.jsx
try { (() => {
/**
 * Eyebrow — small tracked-out uppercase label that sits above section
 * headings. Optional leading tick mark in the accent color.
 */
function Eyebrow({
  children,
  color = "tomato",
  tick = true,
  style,
  ...rest
}) {
  const colors = {
    tomato: "var(--rk-tomato)",
    macaroni: "var(--rk-macaroni-600)",
    muffin: "var(--rk-rhino-500)",
    white: "var(--rk-macaroni-500)"
  };
  const c = colors[color] || colors.tomato;
  return React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 13,
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      color: c,
      ...style
    },
    ...rest
  }, [tick ? React.createElement("span", {
    key: "t",
    style: {
      width: 18,
      height: 2,
      background: c,
      display: "inline-block"
    }
  }) : null, React.createElement("span", {
    key: "l"
  }, children)]);
}
Object.assign(__ds_scope, { Eyebrow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Eyebrow.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
/**
 * Icon — thin wrapper over Lucide (the system's icon set). Renders a Lucide
 * placeholder and asks the global `lucide` to hydrate it. Pages must load
 * <script src="https://unpkg.com/lucide@latest"></script> once.
 * name = any Lucide icon id (e.g. "arrow-right", "upload", "file-text").
 */
function Icon({
  name,
  size = 20,
  strokeWidth = 2,
  color = "currentColor",
  style,
  ...rest
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  }, [name, size]);
  return React.createElement("i", {
    ref,
    "data-lucide": name,
    width: size,
    height: size,
    style: {
      display: "inline-flex",
      color,
      strokeWidth,
      verticalAlign: "middle",
      ...style
    },
    ...rest
  });
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/Link.jsx
try { (() => {
/**
 * Text link in the Report Kitchen tomato style. `emphasis="macaroni"` swaps
 * to a thick macaroni underline for high-spotlight inline links.
 */
function Link({
  children,
  href = "#",
  emphasis = "default",
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const macaroni = emphasis === "macaroni";
  const base = {
    color: macaroni ? "var(--rk-rhino-900)" : "var(--rk-text-link)",
    fontFamily: "var(--rk-font-body)",
    fontWeight: 600,
    textDecoration: "none",
    backgroundImage: macaroni ? "linear-gradient(var(--rk-macaroni-500), var(--rk-macaroni-500))" : "linear-gradient(currentColor, currentColor)",
    backgroundSize: hover || macaroni ? "100% 2px" : "0% 2px",
    backgroundPosition: macaroni ? "0 100%" : "0 100%",
    backgroundRepeat: "no-repeat",
    paddingBottom: 1,
    transition: "background-size var(--rk-dur) var(--rk-ease-out), color var(--rk-dur)",
    ...style
  };
  if (macaroni) base.backgroundSize = "100% 6px";
  return React.createElement("a", {
    href,
    style: base,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    ...rest
  }, children);
}
Object.assign(__ds_scope, { Link });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Link.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
/**
 * Small pill Tag for topics / categories (e.g. "Housing", "Toolkit").
 * tone: neutral | tomato | macaroni | muffin | rhino. `interactive` adds
 * hover affordance for filter chips.
 */
function Tag({
  children,
  tone = "neutral",
  interactive = false,
  active = false,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const tones = {
    neutral: {
      bg: "var(--rk-white)",
      fg: "var(--rk-rhino-700)",
      bd: "var(--rk-border-strong)"
    },
    tomato: {
      bg: "var(--rk-tomato-100)",
      fg: "var(--rk-tomato-700)",
      bd: "transparent"
    },
    macaroni: {
      bg: "var(--rk-macaroni-100)",
      fg: "var(--rk-macaroni-600)",
      bd: "transparent"
    },
    muffin: {
      bg: "var(--rk-rhino-100)",
      fg: "var(--rk-rhino-700)",
      bd: "transparent"
    },
    rhino: {
      bg: "var(--rk-rhino-700)",
      fg: "#fff",
      bd: "transparent"
    }
  };
  const t = tones[tone] || tones.neutral;
  const isActive = active || interactive && hover;
  const base = {
    display: "inline-flex",
    alignItems: "center",
    fontFamily: "var(--rk-font-body)",
    fontWeight: 600,
    fontSize: 13,
    lineHeight: 1,
    letterSpacing: "0.01em",
    padding: "6px 12px",
    borderRadius: "var(--rk-radius-pill)",
    background: active ? "var(--rk-rhino-700)" : t.bg,
    color: active ? "#fff" : t.fg,
    border: `1px solid ${active ? "transparent" : t.bd}`,
    cursor: interactive ? "pointer" : "default",
    transition: "background var(--rk-dur), color var(--rk-dur)",
    ...style
  };
  if (interactive && hover && !active) base.background = "var(--rk-rhino-100)";
  return React.createElement("span", {
    style: base,
    onMouseEnter: interactive ? () => setHover(true) : undefined,
    onMouseLeave: interactive ? () => setHover(false) : undefined,
    ...rest
  }, children);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
/**
 * Input — labelled text field for contact / signup forms. Optional Lucide
 * icon, helper text, and error state. Focus shows the muffin-blue ring.
 */
function Input({
  label,
  type = "text",
  placeholder,
  icon,
  helper,
  error,
  id,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const fieldId = id || `rk-inp-${Math.random().toString(36).slice(2, 7)}`;
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const borderColor = error ? "var(--rk-danger)" : focus ? "var(--rk-muffin)" : "var(--rk-border-strong)";
  return React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 7,
      ...style
    }
  }, [label ? React.createElement("label", {
    key: "l",
    htmlFor: fieldId,
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 600,
      fontSize: 14,
      color: "var(--rk-text-strong)"
    }
  }, label) : null, React.createElement("div", {
    key: "w",
    style: {
      position: "relative",
      display: "flex",
      alignItems: "center"
    }
  }, [icon ? React.createElement("i", {
    key: "i",
    "data-lucide": icon,
    width: 18,
    height: 18,
    style: {
      strokeWidth: 2,
      position: "absolute",
      left: 14,
      color: "var(--rk-rhino-500)",
      pointerEvents: "none"
    }
  }) : null, React.createElement("input", {
    key: "f",
    id: fieldId,
    type,
    placeholder,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      width: "100%",
      boxSizing: "border-box",
      fontFamily: "var(--rk-font-body)",
      fontSize: 16,
      color: "var(--rk-text-body)",
      padding: icon ? "13px 16px 13px 42px" : "13px 16px",
      background: "var(--rk-white)",
      border: `1.5px solid ${borderColor}`,
      borderRadius: "var(--rk-radius-sm)",
      outline: "none",
      boxShadow: focus ? "var(--rk-ring)" : "none",
      transition: "border-color var(--rk-dur), box-shadow var(--rk-dur)"
    },
    ...rest
  })]), helper || error ? React.createElement("span", {
    key: "h",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 13,
      color: error ? "var(--rk-danger)" : "var(--rk-text-muted)"
    }
  }, error || helper) : null]);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
/**
 * Select — native dropdown styled to match the form field system, with a
 * Lucide chevron. Pass `options` as strings or [{value,label}].
 */
function Select({
  label,
  options = [],
  placeholder = "Select…",
  helper,
  id,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const fieldId = id || `rk-sel-${Math.random().toString(36).slice(2, 7)}`;
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const opts = options.map(o => typeof o === "string" ? {
    value: o,
    label: o
  } : o);
  return React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 7,
      ...style
    }
  }, [label ? React.createElement("label", {
    key: "l",
    htmlFor: fieldId,
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 600,
      fontSize: 14,
      color: "var(--rk-text-strong)"
    }
  }, label) : null, React.createElement("div", {
    key: "w",
    style: {
      position: "relative",
      display: "flex",
      alignItems: "center"
    }
  }, [React.createElement("select", {
    key: "f",
    id: fieldId,
    defaultValue: "",
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      width: "100%",
      boxSizing: "border-box",
      appearance: "none",
      fontFamily: "var(--rk-font-body)",
      fontSize: 16,
      color: "var(--rk-text-body)",
      padding: "13px 42px 13px 16px",
      background: "var(--rk-white)",
      border: `1.5px solid ${focus ? "var(--rk-muffin)" : "var(--rk-border-strong)"}`,
      borderRadius: "var(--rk-radius-sm)",
      outline: "none",
      cursor: "pointer",
      boxShadow: focus ? "var(--rk-ring)" : "none",
      transition: "border-color var(--rk-dur), box-shadow var(--rk-dur)"
    },
    ...rest
  }, [React.createElement("option", {
    key: "ph",
    value: "",
    disabled: true
  }, placeholder), ...opts.map((o, i) => React.createElement("option", {
    key: i,
    value: o.value
  }, o.label))]), React.createElement("i", {
    key: "c",
    "data-lucide": "chevron-down",
    width: 18,
    height: 18,
    style: {
      strokeWidth: 2,
      position: "absolute",
      right: 14,
      color: "var(--rk-rhino-500)",
      pointerEvents: "none"
    }
  })]), helper ? React.createElement("span", {
    key: "h",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 13,
      color: "var(--rk-text-muted)"
    }
  }, helper) : null]);
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Textarea.jsx
try { (() => {
/**
 * Textarea — multi-line field for "tell us about your report" contact forms.
 */
function Textarea({
  label,
  placeholder,
  rows = 4,
  helper,
  error,
  id,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const fieldId = id || `rk-ta-${Math.random().toString(36).slice(2, 7)}`;
  const borderColor = error ? "var(--rk-danger)" : focus ? "var(--rk-muffin)" : "var(--rk-border-strong)";
  return React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 7,
      ...style
    }
  }, [label ? React.createElement("label", {
    key: "l",
    htmlFor: fieldId,
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 600,
      fontSize: 14,
      color: "var(--rk-text-strong)"
    }
  }, label) : null, React.createElement("textarea", {
    key: "f",
    id: fieldId,
    rows,
    placeholder,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      width: "100%",
      boxSizing: "border-box",
      fontFamily: "var(--rk-font-body)",
      fontSize: 16,
      lineHeight: 1.5,
      color: "var(--rk-text-body)",
      padding: "13px 16px",
      background: "var(--rk-white)",
      border: `1.5px solid ${borderColor}`,
      borderRadius: "var(--rk-radius-sm)",
      outline: "none",
      resize: "vertical",
      boxShadow: focus ? "var(--rk-ring)" : "none",
      transition: "border-color var(--rk-dur), box-shadow var(--rk-dur)"
    },
    ...rest
  }), helper || error ? React.createElement("span", {
    key: "h",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 13,
      color: error ? "var(--rk-danger)" : "var(--rk-text-muted)"
    }
  }, error || helper) : null]);
}
Object.assign(__ds_scope, { Textarea });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Textarea.jsx", error: String((e && e.message) || e) }); }

// components/layout/Accordion.jsx
try { (() => {
/**
 * Accordion — layered/expandable content, the pattern Report Kitchen uses to
 * make long toolkits scannable. Pass `items` as [{ q, a }]. Single-open by
 * default; set `multi` to allow several open at once.
 */
function Accordion({
  items = [],
  multi = false,
  defaultOpen = [0],
  style,
  ...rest
}) {
  const [open, setOpen] = React.useState(new Set(defaultOpen));
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const toggle = i => {
    setOpen(prev => {
      const next = new Set(multi ? prev : []);
      if (prev.has(i)) next.delete(i);else next.add(i);
      return next;
    });
  };
  return React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      background: "var(--rk-surface-card)",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-md)",
      overflow: "hidden",
      ...style
    },
    ...rest
  }, items.map((it, i) => {
    const isOpen = open.has(i);
    return React.createElement("div", {
      key: i,
      style: {
        borderTop: i === 0 ? "none" : "1px solid var(--rk-border)"
      }
    }, [React.createElement("button", {
      key: "h",
      onClick: () => toggle(i),
      style: {
        all: "unset",
        boxSizing: "border-box",
        width: "100%",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        padding: "20px 24px",
        fontFamily: "var(--rk-font-display)",
        fontWeight: 600,
        fontSize: 19,
        color: "var(--rk-text-strong)"
      }
    }, [React.createElement("span", {
      key: "q"
    }, it.q), React.createElement("i", {
      key: "i",
      "data-lucide": "plus",
      width: 22,
      height: 22,
      style: {
        strokeWidth: 2,
        flexShrink: 0,
        color: "var(--rk-tomato-500)",
        transform: isOpen ? "rotate(45deg)" : "rotate(0)",
        transition: "transform var(--rk-dur) var(--rk-ease-out)"
      }
    })]), React.createElement("div", {
      key: "p",
      style: {
        display: "grid",
        gridTemplateRows: isOpen ? "1fr" : "0fr",
        transition: "grid-template-rows var(--rk-dur-slow) var(--rk-ease-out)"
      }
    }, React.createElement("div", {
      style: {
        overflow: "hidden"
      }
    }, React.createElement("div", {
      style: {
        padding: "0 24px 22px",
        fontFamily: "var(--rk-font-body)",
        fontSize: 16,
        lineHeight: 1.62,
        color: "var(--rk-text-muted)"
      }
    }, it.a)))]);
  }));
}
Object.assign(__ds_scope, { Accordion });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/layout/Accordion.jsx", error: String((e && e.message) || e) }); }

// components/layout/Callout.jsx
try { (() => {
// Whisk mark inlined as SVG so the component is portable at any path depth
// (no external asset request). Fill follows the `color` prop.
const WHISK_PATHS = ["M16.1,4.7c0-1-0.8-1.8-1.7-1.8L1.8,2.7C0.8,2.7,0,3.5,0,4.4c0,1,0.8,1.8,1.7,1.8l12.6,0.2C15.3,6.5,16,5.7,16.1,4.7z M0.8,4.5c0-0.4,0.4-0.8,0.8-0.8c0.4,0,0.8,0.4,0.8,0.8c0,0.4-0.4,0.8-0.8,0.8C1.2,5.2,0.8,4.9,0.8,4.5z", "M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.2C20.8,4.4,34.5,0,37.2,0c2.8,0,5,2.4,5,5.2c0,2.8-2.4,5.1-5.2,5l0,0c-2.7,0-16.2-4.9-16.8-5.1C20.1,5,20,4.9,20,4.8z M41.7,5.1c0-2.5-2-4.5-4.5-4.6c-2.3,0-13.2,3.4-16.1,4.3c2.9,1,13.7,4.8,16,4.9C39.5,9.7,41.6,7.7,41.7,5.1z", "M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.2c0.6-0.1,14.3-2.8,16.9-2.8c2.8,0,5,1.6,5,3.4c0,0.9-0.6,1.8-1.6,2.4c-1,0.6-2.2,0.9-3.6,0.9c-2.7,0-16.2-3.3-16.8-3.4C20.1,5,20,4.9,20,4.8z M41.7,5.1c0-1.5-2-2.8-4.5-2.9c-2.2,0-12.2,1.9-15.7,2.6C24.8,5.6,34.8,7.9,37,7.9c1.2,0,2.4-0.3,3.3-0.8C41.2,6.6,41.6,5.9,41.7,5.1z", "M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.3c0.6,0,14.2-1,16.9-0.9c1.3,0,2.5,0.2,3.5,0.4c1.1,0.3,1.6,0.7,1.6,1.1c0,1-2.7,1.4-5.1,1.4l0,0c-2.7,0-16.2-1.4-16.8-1.5C20.1,5,20,4.9,20,4.8z M41.7,5.2c0-0.1-0.2-0.4-1.2-0.6c-0.9-0.2-2.1-0.4-3.4-0.4c-1.9,0-9.5,0.4-13.8,0.7C27.6,5.3,35.2,6,37.1,6C40,6.1,41.6,5.5,41.7,5.2z"];
function WhiskMark({
  color,
  style
}) {
  return React.createElement("svg", {
    viewBox: "0 0 42.2 10.2",
    width: 210,
    height: 51,
    fill: color,
    "aria-hidden": "true",
    style
  }, [...WHISK_PATHS.map((d, i) => React.createElement("path", {
    key: i,
    d
  })), React.createElement("rect", {
    key: "r",
    x: 18,
    y: 2.3,
    width: 1.9,
    height: 4.9,
    transform: "matrix(0.01756758 -0.9998 0.9998 0.01756758 13.783 23.5703)"
  })]);
}

/**
 * Callout — full-width CTA band. tone: rhino (default dark), tomato, cream.
 * Optional whisk accent in the corner (the one sanctioned decorative use).
 */
function Callout({
  eyebrow,
  title,
  children,
  primaryLabel = "Contact the Kitchen",
  primaryHref = "#",
  onClickPrimary,
  secondaryLabel,
  secondaryHref = "#",
  onClickSecondary,
  tone = "rhino",
  whisk = true,
  style,
  ...rest
}) {
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const tones = {
    rhino: {
      bg: "var(--rk-rhino-700)",
      fg: "#fff",
      sub: "var(--rk-text-on-dark)",
      eb: "var(--rk-macaroni-500)",
      whisk: "#fff",
      primary: "accent"
    },
    tomato: {
      bg: "var(--rk-tomato-500)",
      fg: "#fff",
      sub: "rgba(255,255,255,0.9)",
      eb: "#fff",
      whisk: "#fff",
      primary: "light"
    },
    cream: {
      bg: "var(--rk-cream)",
      fg: "var(--rk-rhino-900)",
      sub: "var(--rk-text-muted)",
      eb: "var(--rk-tomato)",
      whisk: "var(--rk-rhino-700)",
      primary: "brand"
    }
  };
  const t = tones[tone] || tones.rhino;
  const btn = (label, href, kind, onClick) => {
    const styles = {
      accent: {
        bg: "var(--rk-macaroni-500)",
        fg: "var(--rk-rhino-900)"
      },
      brand: {
        bg: "var(--rk-tomato-500)",
        fg: "#fff"
      },
      light: {
        bg: "#fff",
        fg: "var(--rk-tomato-600)"
      }
    }[kind];
    return React.createElement("a", {
      key: "p",
      href,
      onClick,
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        fontFamily: "var(--rk-font-body)",
        fontWeight: 700,
        fontSize: 16,
        padding: "14px 26px",
        borderRadius: "var(--rk-radius-sm)",
        background: styles.bg,
        color: styles.fg,
        textDecoration: "none",
        cursor: "pointer"
      }
    }, [React.createElement("span", {
      key: "l"
    }, label), React.createElement("i", {
      key: "a",
      "data-lucide": "arrow-right",
      width: 18,
      height: 18,
      style: {
        strokeWidth: 2.25
      }
    })]);
  };
  return React.createElement("div", {
    style: {
      position: "relative",
      overflow: "hidden",
      background: t.bg,
      color: t.fg,
      borderRadius: "var(--rk-radius-xl)",
      padding: "56px 52px",
      display: "flex",
      flexDirection: "column",
      gap: 18,
      alignItems: "flex-start",
      ...style
    },
    ...rest
  }, [whisk ? React.createElement(WhiskMark, {
    key: "w",
    color: t.whisk,
    style: {
      position: "absolute",
      right: -10,
      top: 22,
      opacity: 0.16,
      transform: "rotate(-8deg)",
      pointerEvents: "none"
    }
  }) : null, eyebrow ? React.createElement("span", {
    key: "e",
    style: {
      position: "relative",
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 13,
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      color: t.eb
    }
  }, eyebrow) : null, React.createElement("h2", {
    key: "t",
    style: {
      position: "relative",
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 42,
      lineHeight: 1.08,
      letterSpacing: "-0.02em",
      maxWidth: 620,
      textWrap: "balance"
    }
  }, title), children ? React.createElement("p", {
    key: "c",
    style: {
      position: "relative",
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 18,
      lineHeight: 1.6,
      color: t.sub,
      maxWidth: 560
    }
  }, children) : null, React.createElement("div", {
    key: "cta",
    style: {
      position: "relative",
      display: "flex",
      gap: 12,
      flexWrap: "wrap",
      marginTop: 6
    }
  }, [btn(primaryLabel, primaryHref, t.primary, onClickPrimary), secondaryLabel ? React.createElement("a", {
    key: "s",
    href: secondaryHref,
    onClick: onClickSecondary,
    style: {
      display: "inline-flex",
      alignItems: "center",
      padding: "14px 22px",
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 16,
      color: t.fg,
      textDecoration: "none",
      opacity: 0.9,
      cursor: "pointer"
    }
  }, secondaryLabel) : null])]);
}
Object.assign(__ds_scope, { Callout });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/layout/Callout.jsx", error: String((e && e.message) || e) }); }

// components/layout/Card.jsx
try { (() => {
/**
 * ProjectCard — the "Our Work" tile. Photo-free: the cover is a flat color
 * block carrying an oversized Lucide icon and the client/format label. Hover
 * lifts the card and shifts the title to tomato.
 */
function Card({
  title,
  description,
  client,
  tags = [],
  coverColor = "var(--rk-rhino-700)",
  coverIcon = "file-text",
  coverText,
  href = "#",
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  return React.createElement("a", {
    href,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: "flex",
      flexDirection: "column",
      background: "var(--rk-surface-card)",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-lg)",
      overflow: "hidden",
      textDecoration: "none",
      boxShadow: hover ? "var(--rk-shadow-md)" : "none",
      transform: hover ? "translateY(-3px)" : "translateY(0)",
      transition: "transform var(--rk-dur) var(--rk-ease-out), box-shadow var(--rk-dur) var(--rk-ease-out)",
      ...style
    },
    ...rest
  }, [
  // cover
  React.createElement("div", {
    key: "cover",
    style: {
      position: "relative",
      aspectRatio: "16 / 10",
      background: coverColor,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      overflow: "hidden"
    }
  }, [React.createElement("i", {
    key: "ic",
    "data-lucide": coverIcon,
    width: 64,
    height: 64,
    style: {
      strokeWidth: 1.5,
      color: "rgba(255,255,255,0.92)"
    }
  }), coverText ? React.createElement("span", {
    key: "ct",
    style: {
      position: "absolute",
      bottom: 14,
      left: 16,
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 12,
      letterSpacing: "0.06em",
      textTransform: "uppercase",
      color: "rgba(255,255,255,0.85)"
    }
  }, coverText) : null]),
  // body
  React.createElement("div", {
    key: "body",
    style: {
      padding: "20px 22px 22px",
      display: "flex",
      flexDirection: "column",
      gap: 10,
      flex: 1
    }
  }, [client ? React.createElement("span", {
    key: "cl",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: "0.07em",
      color: "var(--rk-tomato)"
    }
  }, client) : null, React.createElement("h3", {
    key: "t",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 22,
      lineHeight: 1.15,
      letterSpacing: "-0.01em",
      color: hover ? "var(--rk-tomato)" : "var(--rk-text-strong)",
      transition: "color var(--rk-dur)"
    }
  }, title), description ? React.createElement("p", {
    key: "d",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 15,
      lineHeight: 1.55,
      color: "var(--rk-text-muted)"
    }
  }, description) : null, tags.length ? React.createElement("div", {
    key: "tg",
    style: {
      display: "flex",
      flexWrap: "wrap",
      gap: 6,
      marginTop: 4
    }
  }, tags.map((t, i) => React.createElement("span", {
    key: i,
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 600,
      fontSize: 12,
      padding: "4px 10px",
      borderRadius: "var(--rk-radius-pill)",
      background: "var(--rk-gray-100)",
      color: "var(--rk-rhino-700)"
    }
  }, t))) : null])]);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/layout/Card.jsx", error: String((e && e.message) || e) }); }

// components/layout/FeatureCard.jsx
try { (() => {
/**
 * FeatureCard — used for offerings and value props. Icon tile, title, body,
 * optional availability Badge and a trailing action link. Hover nudges the
 * arrow and lifts the card.
 */
function FeatureCard({
  icon = "sparkles",
  title,
  children,
  badge,
  badgeTone = "success",
  action,
  href = "#",
  accent = "tomato",
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const accents = {
    tomato: {
      bg: "var(--rk-tomato-100)",
      fg: "var(--rk-tomato-600)"
    },
    macaroni: {
      bg: "var(--rk-macaroni-100)",
      fg: "var(--rk-macaroni-600)"
    },
    muffin: {
      bg: "var(--rk-rhino-100)",
      fg: "var(--rk-rhino-500)"
    },
    rhino: {
      bg: "var(--rk-rhino-100)",
      fg: "var(--rk-rhino-700)"
    }
  };
  const a = accents[accent] || accents.tomato;
  const badgeTones = {
    success: {
      bg: "rgba(46,139,87,0.12)",
      fg: "#1F6B41"
    },
    soon: {
      bg: "var(--rk-macaroni-100)",
      fg: "var(--rk-macaroni-600)"
    },
    brand: {
      bg: "var(--rk-tomato-100)",
      fg: "var(--rk-tomato-700)"
    }
  };
  const bt = badgeTones[badgeTone] || badgeTones.success;
  const wrap = {
    display: "flex",
    flexDirection: "column",
    gap: 14,
    padding: "28px",
    background: "var(--rk-surface-card)",
    border: "1px solid var(--rk-border)",
    borderRadius: "var(--rk-radius-lg)",
    textDecoration: "none",
    boxShadow: hover ? "var(--rk-shadow-md)" : "none",
    transform: hover ? "translateY(-3px)" : "translateY(0)",
    transition: "transform var(--rk-dur) var(--rk-ease-out), box-shadow var(--rk-dur) var(--rk-ease-out)",
    ...style
  };
  return React.createElement(action ? "a" : "div", {
    href: action ? href : undefined,
    style: wrap,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    ...rest
  }, [React.createElement("div", {
    key: "top",
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, [React.createElement("div", {
    key: "ico",
    style: {
      width: 52,
      height: 52,
      borderRadius: "var(--rk-radius-md)",
      background: a.bg,
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, React.createElement("i", {
    "data-lucide": icon,
    width: 26,
    height: 26,
    style: {
      strokeWidth: 2,
      color: a.fg
    }
  })), badge ? React.createElement("span", {
    key: "b",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: "0.06em",
      padding: "5px 10px",
      borderRadius: "var(--rk-radius-xs)",
      background: bt.bg,
      color: bt.fg
    }
  }, badge) : null]), React.createElement("h3", {
    key: "t",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 22,
      lineHeight: 1.15,
      letterSpacing: "-0.01em",
      color: "var(--rk-text-strong)"
    }
  }, title), children ? React.createElement("p", {
    key: "c",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 15.5,
      lineHeight: 1.6,
      color: "var(--rk-text-muted)"
    }
  }, children) : null, action ? React.createElement("span", {
    key: "a",
    style: {
      marginTop: "auto",
      display: "inline-flex",
      alignItems: "center",
      gap: 7,
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 15,
      color: "var(--rk-tomato-600)"
    }
  }, [React.createElement("span", {
    key: "l"
  }, action), React.createElement("i", {
    key: "arr",
    "data-lucide": "arrow-right",
    width: 17,
    height: 17,
    style: {
      strokeWidth: 2.25,
      transform: hover ? "translateX(4px)" : "translateX(0)",
      transition: "transform var(--rk-dur) var(--rk-ease-out)"
    }
  })]) : null]);
}
Object.assign(__ds_scope, { FeatureCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/layout/FeatureCard.jsx", error: String((e && e.message) || e) }); }

// components/layout/SectionHeading.jsx
try { (() => {
/**
 * SectionHeading — eyebrow + display title + optional intro paragraph.
 * align: left | center. `inverse` for use on rhino/dark grounds.
 */
function SectionHeading({
  eyebrow,
  eyebrowColor = "tomato",
  title,
  intro,
  align = "left",
  inverse = false,
  size = "lg",
  style,
  ...rest
}) {
  const titleSize = size === "sm" ? 28 : size === "md" ? 36 : 48;
  const ec = {
    tomato: "var(--rk-tomato)",
    macaroni: "var(--rk-macaroni-500)",
    muffin: "var(--rk-rhino-500)"
  }[eyebrowColor] || "var(--rk-tomato)";
  return React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 14,
      alignItems: align === "center" ? "center" : "flex-start",
      textAlign: align,
      maxWidth: align === "center" ? 720 : "none",
      marginLeft: align === "center" ? "auto" : undefined,
      marginRight: align === "center" ? "auto" : undefined,
      ...style
    },
    ...rest
  }, [eyebrow ? React.createElement("span", {
    key: "e",
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 13,
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      color: ec
    }
  }, [React.createElement("span", {
    key: "t",
    style: {
      width: 18,
      height: 2,
      background: ec
    }
  }), React.createElement("span", {
    key: "x"
  }, eyebrow)]) : null, React.createElement("h2", {
    key: "t",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: titleSize,
      lineHeight: 1.08,
      letterSpacing: "-0.02em",
      color: inverse ? "#fff" : "var(--rk-text-strong)",
      textWrap: "balance"
    }
  }, title), intro ? React.createElement("p", {
    key: "i",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 18,
      lineHeight: 1.6,
      color: inverse ? "var(--rk-text-on-dark)" : "var(--rk-text-muted)",
      maxWidth: 640
    }
  }, intro) : null]);
}
Object.assign(__ds_scope, { SectionHeading });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/layout/SectionHeading.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/About.jsx
try { (() => {
// Report Kitchen website — About (single page; story + values, photo-free)
const RKa = window.ReportKitchenDesignSystem_07c3a7;
const ha = React.createElement;
function About({
  go
}) {
  const {
    Eyebrow,
    SectionHeading,
    Callout,
    Button
  } = RKa;
  const wrap = {
    maxWidth: 1080,
    margin: "0 auto",
    padding: "0 40px"
  };
  const narrow = {
    maxWidth: 760,
    margin: "0 auto",
    padding: "0 40px"
  };
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const values = [{
    icon: "unlock",
    t: "Free the content",
    b: "The PDF is 25-year-old technology — conceived before smartphones, social media, or even Google. Your reports deserve modern, standards-compliant HTML."
  }, {
    icon: "accessibility",
    t: "Accessible by default",
    b: "Real semantic structure, keyboard navigation, and screen-reader support on every build. Accessibility is a value, not an add-on."
  }, {
    icon: "line-chart",
    t: "Built to be measured",
    b: "Video, mobile, dataviz, social, and full analytics — so you finally know what readers engage with."
  }];
  const p = (txt, key) => ha("p", {
    key,
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 19,
      lineHeight: 1.7,
      color: "var(--rk-text-body)"
    }
  }, txt);
  return ha("div", null, [
  // HERO
  ha("section", {
    key: "hero",
    style: {
      background: "var(--rk-cream)",
      padding: "72px 0 64px",
      borderBottom: "1px solid var(--rk-border)"
    }
  }, ha("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 20
    }
  }, [ha(Eyebrow, {
    key: "e"
  }, "About the Kitchen"), ha("h1", {
    key: "h",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 52,
      lineHeight: 1.05,
      letterSpacing: "-0.03em",
      color: "var(--rk-text-strong)",
      maxWidth: 880,
      textWrap: "balance"
    }
  }, "We help our clients maximize the impact of their work — to improve our communities and the world.")])),
  // STORY
  ha("section", {
    key: "story",
    style: {
      padding: "72px 0"
    }
  }, ha("div", {
    style: {
      ...narrow,
      display: "flex",
      flexDirection: "column",
      gap: 24
    }
  }, [ha("span", {
    key: "k",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 13,
      textTransform: "uppercase",
      letterSpacing: ".08em",
      color: "var(--rk-tomato)"
    }
  }, "Our story"), p("The team behind Report Kitchen began building websites for nonprofits, foundations, and higher-education clients way back in 1999. As our capabilities with data, analytics, and visualization grew, we started working with more research and policy organizations — and we noticed some trends.", "s1"), p("The first was that these organizations produced a ton of PDF reports. The second was that nobody was reading them. We soon learned others in the field were having the same experience.", "s2"), p("We started brainstorming ways to make these reports more usable and engaging, and it came down to freeing them from the constraints of the PDF — a 25-year-old technology conceived before smartphones, social media, or even Google. The content needed modern, standards-compliant HTML. But writing and editing documents this size in the clumsy editors inside a CMS just wasn't realistic for most teams.", "s3"), p("So we built a suite of tools and processes to extract all the text, images, charts, and other content from Word or PDF documents, convert it to HTML, and assemble a web-based digital document with all the features you'd expect today — video, mobile, dataviz, social media, analytics, and much more. We call that platform Report Kitchen, and it's now the primary focus of our company.", "s4"), p("So while the platform is brand new, we bring over 20 years of experience designing and developing great web experiences for nonprofit, higher-ed, government, and corporate clients.", "s5")])),
  // VALUES
  ha("section", {
    key: "vals",
    style: {
      background: "#fff",
      borderTop: "1px solid var(--rk-border)",
      borderBottom: "1px solid var(--rk-border)",
      padding: "72px 0"
    }
  }, ha("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 40
    }
  }, [ha(SectionHeading, {
    key: "sh",
    eyebrow: "How we cook",
    title: "The principles behind every build"
  }), ha("div", {
    key: "g",
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 22
    }
  }, values.map((v, i) => ha("div", {
    key: i,
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 14,
      padding: 26,
      background: "var(--rk-paper)",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-lg)"
    }
  }, [ha("div", {
    key: "ic",
    style: {
      width: 50,
      height: 50,
      borderRadius: "var(--rk-radius-md)",
      background: "var(--rk-macaroni-100)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, ha("i", {
    "data-lucide": v.icon,
    width: 25,
    height: 25,
    style: {
      strokeWidth: 1.9,
      color: "var(--rk-macaroni-600)"
    }
  })), ha("h3", {
    key: "t",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 20,
      color: "var(--rk-text-strong)"
    }
  }, v.t), ha("p", {
    key: "b",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 15.5,
      lineHeight: 1.6,
      color: "var(--rk-text-muted)"
    }
  }, v.b)])))])),
  // EXPERIENCE STAT STRIP
  ha("section", {
    key: "stats",
    style: {
      padding: "64px 0"
    }
  }, ha("div", {
    style: {
      ...wrap,
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 24
    }
  }, [["20+ yrs", "designing web experiences"], ["1999", "building for mission-driven teams"], ["100%", "WCAG AA accessible builds"]].map((s, i) => ha("div", {
    key: i,
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 6,
      padding: "8px 0",
      borderTop: "3px solid var(--rk-tomato-500)"
    }
  }, [ha("span", {
    key: "n",
    style: {
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 46,
      letterSpacing: "-0.02em",
      color: "var(--rk-rhino-900)"
    }
  }, s[0]), ha("span", {
    key: "l",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 16,
      color: "var(--rk-text-muted)"
    }
  }, s[1])])))),
  // CTA
  ha("section", {
    key: "cta",
    style: {
      padding: "0 0 88px"
    }
  }, ha("div", {
    style: wrap
  }, ha(Callout, {
    eyebrow: "Let's work together",
    title: "Let's make your reports more interactive, engaging, and successful.",
    primaryLabel: "Contact the Kitchen",
    secondaryLabel: "See our work",
    onClickSecondary: () => go("work")
  }, "Contact us today — we'd love to help your research reports and policy documents reach the audience they deserve.")))]);
}
window.RKSite = window.RKSite || {};
window.RKSite.About = About;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/About.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Header.jsx
try { (() => {
// Report Kitchen website — shared Header + Footer
// Reads primitives from the DS bundle; exposes RKSite.Header / RKSite.Footer.
const RKe = React.createElement;
function Header({
  current,
  go
}) {
  const {
    Button
  } = window.ReportKitchenDesignSystem_07c3a7;
  const [openMenu, setOpenMenu] = React.useState(false);
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const nav = [{
    id: "work",
    label: "Our Work"
  }, {
    id: "insights",
    label: "Insights"
  }, {
    id: "about",
    label: "About"
  }];
  const services = [{
    id: "maker",
    label: "Landing Page Maker",
    note: "Available now",
    icon: "wand-sparkles",
    desc: "Upload a PDF and build a polished landing page for it — free for individuals, paid for teams."
  }, {
    id: "express",
    label: "Report Kitchen Express",
    note: "Coming soon",
    icon: "globe",
    desc: "Upload a PDF and get a fully responsive HTML website, automatically. Free & paid tiers."
  }, {
    id: "custom",
    label: "Report Kitchen Custom",
    note: "Available now",
    icon: "chef-hat",
    desc: "Hand us your PDF; we build you a bespoke, responsive, accessible website end to end."
  }, {
    id: "consulting",
    label: "Consulting",
    note: "Available now",
    icon: "messages-square",
    desc: "Guidance at the intersection of nonprofit communications, long-form reports, and AI."
  }];
  return RKe("header", {
    style: {
      position: "sticky",
      top: 0,
      zIndex: 50,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "16px 40px",
      background: "rgba(251,247,240,0.86)",
      backdropFilter: "blur(10px)",
      borderBottom: "1px solid var(--rk-border)"
    }
  }, [RKe("a", {
    key: "logo",
    href: "#",
    onClick: e => {
      e.preventDefault();
      go("home");
    },
    style: {
      display: "flex",
      alignItems: "center"
    }
  }, RKe("img", {
    src: "../../assets/logo-red.svg",
    alt: "Report Kitchen",
    style: {
      height: 38
    }
  })), RKe("nav", {
    key: "nav",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 4
    }
  }, [
  // SERVICES megamenu
  RKe("div", {
    key: "svc",
    style: {
      position: "static"
    },
    onMouseEnter: () => setOpenMenu(true),
    onMouseLeave: () => setOpenMenu(false)
  }, [RKe("button", {
    key: "b",
    style: navLink(openMenu),
    onClick: () => go("custom")
  }, ["Services", RKe("i", {
    key: "c",
    "data-lucide": "chevron-down",
    width: 15,
    height: 15,
    style: {
      strokeWidth: 2.25,
      marginLeft: 4,
      transform: openMenu ? "rotate(180deg)" : "none",
      transition: "transform var(--rk-dur)"
    }
  })]), openMenu ? RKe("div", {
    key: "m",
    style: {
      position: "absolute",
      top: "100%",
      left: 40,
      right: 40,
      background: "#fff",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-lg)",
      boxShadow: "var(--rk-shadow-lg)",
      padding: 20,
      marginTop: 8,
      display: "grid",
      gridTemplateColumns: "repeat(2, 1fr)",
      gap: 8
    }
  }, [RKe("div", {
    key: "hd",
    style: {
      gridColumn: "1 / -1",
      display: "flex",
      alignItems: "baseline",
      justifyContent: "space-between",
      padding: "2px 8px 10px",
      marginBottom: 4,
      borderBottom: "1px solid var(--rk-border)"
    }
  }, [RKe("span", {
    key: "t",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: ".08em",
      color: "var(--rk-tomato)"
    }
  }, "What's on the menu"), RKe("span", {
    key: "s",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 13,
      color: "var(--rk-text-muted)"
    }
  }, "Four ways to serve your work")]), ...services.map(o => RKe("a", {
    key: o.id,
    href: "#",
    onClick: e => {
      e.preventDefault();
      go(o.id);
    },
    style: {
      display: "flex",
      gap: 14,
      padding: "14px 12px",
      borderRadius: "var(--rk-radius-md)",
      textDecoration: "none"
    },
    onMouseEnter: e => e.currentTarget.style.background = "var(--rk-gray-100)",
    onMouseLeave: e => e.currentTarget.style.background = "transparent"
  }, [RKe("div", {
    key: "ic",
    style: {
      flexShrink: 0,
      width: 42,
      height: 42,
      borderRadius: "var(--rk-radius-md)",
      background: "var(--rk-tomato-100)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, RKe("i", {
    "data-lucide": o.icon,
    width: 22,
    height: 22,
    style: {
      strokeWidth: 2,
      color: "var(--rk-tomato-600)"
    }
  })), RKe("div", {
    key: "tx",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 3
    }
  }, [RKe("div", {
    key: "top",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8
    }
  }, [RKe("span", {
    key: "l",
    style: {
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 16,
      color: "var(--rk-text-strong)"
    }
  }, o.label), RKe("span", {
    key: "n",
    style: {
      fontSize: 10.5,
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: ".05em",
      padding: "2px 7px",
      borderRadius: 999,
      background: o.note === "Coming soon" ? "var(--rk-macaroni-100)" : "rgba(46,139,87,0.12)",
      color: o.note === "Coming soon" ? "var(--rk-macaroni-600)" : "#1F6B41"
    }
  }, o.note)]), RKe("span", {
    key: "d",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 13.5,
      lineHeight: 1.45,
      color: "var(--rk-text-muted)"
    }
  }, o.desc)])]))]) : null]), ...nav.map(n => RKe("a", {
    key: n.id,
    href: "#",
    onClick: e => {
      e.preventDefault();
      go(n.id);
    },
    style: navLink(current === n.id)
  }, n.label)),
  // PATTERN LIBRARY — set off as a distinct free resource
  RKe("a", {
    key: "patterns",
    href: "#",
    onClick: e => {
      e.preventDefault();
      go("patterns");
    },
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 7,
      marginLeft: 6,
      padding: "7px 14px",
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 15,
      textDecoration: "none",
      color: current === "patterns" ? "var(--rk-rhino-900)" : "var(--rk-rhino-700)",
      border: "1.5px solid var(--rk-border-strong)",
      borderRadius: "var(--rk-radius-pill)",
      transition: "border-color var(--rk-dur), background var(--rk-dur)"
    },
    onMouseEnter: e => {
      e.currentTarget.style.borderColor = "var(--rk-macaroni-500)";
      e.currentTarget.style.background = "var(--rk-macaroni-100)";
    },
    onMouseLeave: e => {
      e.currentTarget.style.borderColor = "var(--rk-border-strong)";
      e.currentTarget.style.background = "transparent";
    }
  }, [RKe("i", {
    key: "i",
    "data-lucide": "book-open",
    width: 16,
    height: 16,
    style: {
      strokeWidth: 2,
      color: "var(--rk-macaroni-600)"
    }
  }), "Pattern Library"]), RKe("div", {
    key: "cta",
    style: {
      marginLeft: 10
    }
  }, RKe(Button, {
    size: "sm",
    iconRight: "arrow-right",
    onClick: () => go("custom")
  }, "Contact the Kitchen"))])]);
}
function navLink(active) {
  return {
    display: "inline-flex",
    alignItems: "center",
    background: "none",
    border: "none",
    cursor: "pointer",
    fontFamily: "var(--rk-font-body)",
    fontWeight: 600,
    fontSize: 15,
    color: active ? "var(--rk-tomato-600)" : "var(--rk-rhino-700)",
    textDecoration: "none",
    padding: "8px 14px",
    borderRadius: "var(--rk-radius-sm)"
  };
}
function Footer({
  go
}) {
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const col = (title, links) => RKe("div", {
    key: title,
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, [RKe("span", {
    key: "t",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 13,
      textTransform: "uppercase",
      letterSpacing: ".07em",
      color: "var(--rk-macaroni-500)"
    }
  }, title), ...links.map((l, i) => RKe("a", {
    key: i,
    href: "#",
    onClick: e => {
      e.preventDefault();
      l[1] && go(l[1]);
    },
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 15,
      color: "var(--rk-text-on-dark)",
      textDecoration: "none",
      opacity: 0.85
    }
  }, l[0]))]);
  return RKe("footer", {
    style: {
      background: "var(--rk-rhino-900)",
      color: "#fff",
      padding: "64px 40px 40px",
      position: "relative",
      overflow: "hidden"
    }
  }, [RKe("img", {
    key: "w",
    src: "../../assets/whisk-white.svg",
    alt: "",
    "aria-hidden": "true",
    style: {
      position: "absolute",
      right: -30,
      bottom: -20,
      width: 260,
      opacity: 0.08,
      transform: "rotate(-10deg)"
    }
  }), RKe("div", {
    key: "grid",
    style: {
      position: "relative",
      display: "grid",
      gridTemplateColumns: "1.6fr 1fr 1fr 1fr",
      gap: 40,
      maxWidth: 1200,
      margin: "0 auto"
    }
  }, [RKe("div", {
    key: "brand",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 16
    }
  }, [RKe("img", {
    key: "l",
    src: "../../assets/logo-white.svg",
    alt: "Report Kitchen",
    style: {
      height: 40
    }
  }), RKe("p", {
    key: "p",
    style: {
      margin: 0,
      maxWidth: 300,
      fontFamily: "var(--rk-font-body)",
      fontSize: 15,
      lineHeight: 1.6,
      color: "var(--rk-text-on-dark)",
      opacity: 0.85
    }
  }, "We turn dense PDFs into interactive, accessible websites your audience will actually use."), RKe("div", {
    key: "c",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 15,
      lineHeight: 1.7,
      opacity: 0.85
    }
  }, [RKe("div", {
    key: "e"
  }, "info@reportkitchen.com"), RKe("div", {
    key: "ph"
  }, "215-592-7673")])]), col("Offerings", [["Landing Page Maker", "maker"], ["RK Express", "express"], ["Report Kitchen Custom", "custom"], ["Consulting", "consulting"]]), col("Explore", [["Our Work", "work"], ["Pattern Library", "patterns"], ["Insights", "insights"], ["About", "about"]]), col("Company", [["How we use AI"], ["Privacy Policy"], ["Contact the Kitchen", "custom"]])]), RKe("div", {
    key: "base",
    style: {
      position: "relative",
      maxWidth: 1200,
      margin: "40px auto 0",
      paddingTop: 24,
      borderTop: "1px solid rgba(255,255,255,0.12)",
      display: "flex",
      justifyContent: "space-between",
      fontFamily: "var(--rk-font-body)",
      fontSize: 13,
      color: "rgba(255,255,255,0.55)"
    }
  }, [RKe("span", {
    key: "c"
  }, "© 2025 Report Kitchen"), RKe("span", {
    key: "m"
  }, "Baked with \u2764\uFE0F in Philadelphia")])]);
}
window.RKSite = window.RKSite || {};
window.RKSite.Header = Header;
window.RKSite.Footer = Footer;
window.RKSite.navLink = navLink;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Header.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Home.jsx
try { (() => {
// Report Kitchen website — Home
const RK = window.ReportKitchenDesignSystem_07c3a7;
const h = React.createElement;

// Photo-free hero device: a PDF page transforming into a responsive site.
function PdfToWeb() {
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const line = (w, c = "var(--rk-rhino-200)", k) => h("div", {
    key: k,
    style: {
      height: 7,
      width: w,
      borderRadius: 4,
      background: c
    }
  });
  return h("div", {
    style: {
      position: "relative",
      height: 380,
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, [
  // soft color field behind
  h("div", {
    key: "bg",
    style: {
      position: "absolute",
      inset: "10% 4%",
      background: "var(--rk-macaroni-100)",
      borderRadius: "var(--rk-radius-xl)"
    }
  }),
  // PDF card (left, tilted)
  h("div", {
    key: "pdf",
    style: {
      position: "absolute",
      left: "6%",
      top: 40,
      width: 190,
      background: "#fff",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-sm)",
      boxShadow: "var(--rk-shadow-md)",
      padding: 18,
      transform: "rotate(-5deg)",
      display: "flex",
      flexDirection: "column",
      gap: 9
    }
  }, [h("div", {
    key: "b",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 7,
      marginBottom: 4
    }
  }, [h("i", {
    key: "i",
    "data-lucide": "file-text",
    width: 18,
    height: 18,
    style: {
      strokeWidth: 2,
      color: "var(--rk-tomato-500)"
    }
  }), h("span", {
    key: "t",
    style: {
      fontFamily: "var(--rk-font-mono)",
      fontSize: 11,
      color: "var(--rk-text-muted)"
    }
  }, "report.pdf")]), line("70%", "var(--rk-rhino-300)", "l1"), line("100%", undefined, "l2"), line("92%", undefined, "l3"), line("100%", undefined, "l4"), line("60%", undefined, "l5"), h("div", {
    key: "sp",
    style: {
      height: 4
    }
  }), line("100%", undefined, "l6"), line("80%", undefined, "l7")]),
  // arrow
  h("div", {
    key: "arr",
    style: {
      position: "absolute",
      left: "44%",
      top: 175,
      width: 52,
      height: 52,
      borderRadius: "50%",
      background: "var(--rk-tomato-500)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      boxShadow: "var(--rk-shadow-md)",
      zIndex: 3
    }
  }, h("i", {
    "data-lucide": "arrow-right",
    width: 26,
    height: 26,
    style: {
      strokeWidth: 2.5,
      color: "#fff"
    }
  })),
  // browser card (right)
  h("div", {
    key: "web",
    style: {
      position: "absolute",
      right: "5%",
      top: 60,
      width: 260,
      background: "#fff",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-md)",
      boxShadow: "var(--rk-shadow-lg)",
      overflow: "hidden"
    }
  }, [h("div", {
    key: "bar",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      padding: "10px 12px",
      background: "var(--rk-gray-100)",
      borderBottom: "1px solid var(--rk-border)"
    }
  }, ["#E4614F", "#F2BB2E", "#7683A2"].map((c, i) => h("span", {
    key: i,
    style: {
      width: 9,
      height: 9,
      borderRadius: "50%",
      background: c
    }
  }))), h("div", {
    key: "hero",
    style: {
      background: "var(--rk-rhino-700)",
      padding: "18px 16px",
      display: "flex",
      flexDirection: "column",
      gap: 8
    }
  }, [line("55%", "var(--rk-macaroni-500)", "h1"), line("85%", "rgba(255,255,255,0.85)", "h2"), line("70%", "rgba(255,255,255,0.55)", "h3")]), h("div", {
    key: "body",
    style: {
      padding: 16,
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 10
    }
  }, [h("div", {
    key: "c",
    style: {
      gridColumn: "1 / -1",
      height: 44,
      borderRadius: 8,
      background: "var(--rk-macaroni-100)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, h("i", {
    "data-lucide": "bar-chart-3",
    width: 22,
    height: 22,
    style: {
      color: "var(--rk-macaroni-600)"
    }
  })), h("div", {
    key: "a",
    style: {
      height: 30,
      borderRadius: 6,
      background: "var(--rk-gray-100)"
    }
  }), h("div", {
    key: "b",
    style: {
      height: 30,
      borderRadius: 6,
      background: "var(--rk-gray-100)"
    }
  })])])]);
}
function TrustStrip_unused() {
  const clients = ["Enterprise Community Partners", "Learning Policy Institute", "Charles Stewart Mott Foundation", "Center for Constitutional Rights"];
  return h("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 18,
      alignItems: "center"
    }
  }, [h("span", {
    key: "l",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 13,
      textTransform: "uppercase",
      letterSpacing: ".08em",
      color: "var(--rk-text-muted)"
    }
  }, "Trusted by mission-driven teams"), h("div", {
    key: "row",
    style: {
      display: "flex",
      flexWrap: "wrap",
      gap: "18px 40px",
      justifyContent: "center"
    }
  }, clients.map((c, i) => h("span", {
    key: i,
    style: {
      fontFamily: "var(--rk-font-display)",
      fontWeight: 600,
      fontSize: 18,
      color: "var(--rk-rhino-500)"
    }
  }, c)))]);
}
function Step({
  n,
  icon,
  title,
  body
}) {
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  return h("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 12,
      flex: 1
    }
  }, [h("div", {
    key: "top",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 12
    }
  }, [h("div", {
    key: "ic",
    style: {
      width: 48,
      height: 48,
      borderRadius: "var(--rk-radius-md)",
      background: "#fff",
      border: "1px solid var(--rk-border)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, h("i", {
    "data-lucide": icon,
    width: 24,
    height: 24,
    style: {
      strokeWidth: 2,
      color: "var(--rk-tomato-500)"
    }
  })), h("span", {
    key: "n",
    style: {
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 40,
      color: "var(--rk-rhino-100)"
    }
  }, n)]), h("h3", {
    key: "t",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 22,
      color: "var(--rk-text-strong)"
    }
  }, title), h("p", {
    key: "b",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 15.5,
      lineHeight: 1.6,
      color: "var(--rk-text-muted)"
    }
  }, body)]);
}
function Home({
  go
}) {
  const {
    Button,
    FeatureCard,
    Card,
    SectionHeading,
    Callout,
    Eyebrow
  } = RK;
  const wrap = {
    maxWidth: 1200,
    margin: "0 auto",
    padding: "0 40px"
  };
  return h("div", null, [
  // HERO
  h("section", {
    key: "hero",
    style: {
      padding: "72px 0 84px"
    }
  }, h("div", {
    style: {
      ...wrap,
      display: "grid",
      gridTemplateColumns: "1.05fr 1fr",
      gap: 48,
      alignItems: "center"
    }
  }, [h("div", {
    key: "l",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 24
    }
  }, [h(Eyebrow, {
    key: "e"
  }, "PDF → living website"), h("h1", {
    key: "h",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 60,
      lineHeight: 1.02,
      letterSpacing: "-0.03em",
      color: "var(--rk-text-strong)",
      textWrap: "balance"
    }
  }, ["Your report deserves better than a ", h("span", {
    key: "s",
    style: {
      color: "var(--rk-tomato-500)"
    }
  }, "download button"), "."]), h("p", {
    key: "p",
    style: {
      margin: 0,
      maxWidth: 500,
      fontFamily: "var(--rk-font-body)",
      fontSize: 20,
      lineHeight: 1.55,
      color: "var(--rk-text-muted)"
    }
  }, "Report Kitchen turns dense PDFs into interactive, accessible, fully responsive websites — so your audience can truly engage with your work instead of just downloading it."), h("div", {
    key: "cta",
    style: {
      display: "flex",
      gap: 12,
      flexWrap: "wrap",
      marginTop: 4
    }
  }, [h(Button, {
    key: "a",
    size: "lg",
    iconRight: "arrow-right",
    onClick: () => go("custom")
  }, "Get cooking"), h(Button, {
    key: "b",
    size: "lg",
    variant: "secondary",
    onClick: () => go("work")
  }, "See our work")])]), h("div", {
    key: "r"
  }, h(PdfToWeb))])),
  // OFFERINGS
  h("section", {
    key: "off",
    style: {
      background: "#fff",
      borderTop: "1px solid var(--rk-border)",
      borderBottom: "1px solid var(--rk-border)",
      padding: "80px 0"
    }
  }, h("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 40
    }
  }, [h(SectionHeading, {
    key: "sh",
    eyebrow: "What's on the menu",
    title: "Four ways to serve your work",
    intro: "From self-serve tools to full white-glove builds — pick the level of help you need."
  }), h("div", {
    key: "g",
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(2, 1fr)",
      gap: 20
    }
  }, [h(FeatureCard, {
    key: "1",
    icon: "wand-sparkles",
    title: "Landing Page Maker",
    badge: "Available now",
    badgeTone: "success",
    action: "Start free",
    accent: "tomato",
    onClick: () => go("maker")
  }, "Upload a PDF and build a polished landing page for it — free for individuals, paid for teams."), h(FeatureCard, {
    key: "2",
    icon: "globe",
    title: "Report Kitchen Express",
    badge: "Coming soon",
    badgeTone: "soon",
    action: "Join the waitlist",
    accent: "macaroni",
    onClick: () => go("express")
  }, "Upload a PDF and get a fully responsive HTML website, automatically. Free & paid tiers."), h(FeatureCard, {
    key: "3",
    icon: "chef-hat",
    title: "Report Kitchen Custom",
    badge: "Available now",
    badgeTone: "success",
    action: "Contact the Kitchen",
    accent: "rhino",
    onClick: () => go("custom")
  }, "Hand us your PDF; we build you a bespoke, responsive, accessible website end to end."), h(FeatureCard, {
    key: "4",
    icon: "messages-square",
    title: "Consulting",
    badge: "Available now",
    badgeTone: "success",
    action: "Start a conversation",
    accent: "muffin",
    onClick: () => go("consulting")
  }, "Guidance at the intersection of nonprofit communications, long-form reports, and AI.")])])),
  // HOW IT WORKS
  h("section", {
    key: "how",
    style: {
      background: "var(--rk-cream)",
      padding: "80px 0"
    }
  }, h("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 44
    }
  }, [h(SectionHeading, {
    key: "sh",
    eyebrow: "How it works",
    eyebrowColor: "tomato",
    title: "Three steps, no reformatting headaches"
  }), h("div", {
    key: "s",
    style: {
      display: "flex",
      gap: 40
    }
  }, [h(Step, {
    key: "1",
    n: "01",
    icon: "upload",
    title: "Send us your PDF",
    body: "Report, toolkit, comprehensive plan — whatever you've published. We start from what you already have."
  }), h(Step, {
    key: "2",
    n: "02",
    icon: "cooking-pot",
    title: "We cook it into a site",
    body: "Layered navigation, real accessibility, responsive layouts, charts and interactive content."
  }), h(Step, {
    key: "3",
    n: "03",
    icon: "rocket",
    title: "Publish & measure",
    body: "Launch a site people actually use — with full analytics on what readers engage with."
  })])])),
  // FEATURED WORK
  h("section", {
    key: "work",
    style: {
      padding: "80px 0"
    }
  }, h("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 36
    }
  }, [h("div", {
    key: "hd",
    style: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "flex-end",
      gap: 20
    }
  }, [h(SectionHeading, {
    key: "sh",
    eyebrow: "Our work",
    title: "Reports we've reinvented"
  }), h(Button, {
    key: "b",
    variant: "ghost",
    iconRight: "arrow-right",
    onClick: () => go("work")
  }, "See all work")]), h("div", {
    key: "g",
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 20
    }
  }, [h(Card, {
    key: "1",
    client: "Enterprise Community Partners",
    title: "Housing2Justice National Toolkit",
    description: "Helping the housing industry better understand and serve the justice-impacted population.",
    coverColor: "var(--rk-rhino-700)",
    coverIcon: "scale",
    coverText: "Toolkit",
    tags: ["Housing", "Toolkit"],
    onClick: () => go("profile")
  }), h(Card, {
    key: "2",
    client: "Learning Policy Institute",
    title: "Restarting & Reinventing School",
    description: "A framework to reimagine schooling using safe, equitable, student-centered approaches.",
    coverColor: "var(--rk-tomato-500)",
    coverIcon: "graduation-cap",
    coverText: "Framework",
    tags: ["Education", "Policy"],
    onClick: () => go("profile")
  }), h(Card, {
    key: "3",
    client: "Charles Stewart Mott Foundation",
    title: "Focus on Flint",
    description: "Dozens of charts and infographics across eight issues affecting the Flint community.",
    coverColor: "var(--rk-muffin)",
    coverIcon: "bar-chart-3",
    coverText: "Report",
    tags: ["Data", "Community"],
    onClick: () => go("profile")
  })])])),
  // PATTERN LIBRARY TEASER
  h("section", {
    key: "pat",
    style: {
      background: "var(--rk-rhino-700)",
      padding: "80px 0"
    }
  }, h("div", {
    style: {
      ...wrap,
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 48,
      alignItems: "center"
    }
  }, [h("div", {
    key: "l",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 22
    }
  }, [h(SectionHeading, {
    key: "sh",
    inverse: true,
    eyebrow: "Free resource",
    eyebrowColor: "macaroni",
    title: "The Info Design Pattern Library",
    intro: "A growing, open library of information-design patterns — examples, when to use each, and the tools to build them yourself."
  }), h("div", {
    key: "b"
  }, h(Button, {
    variant: "accent",
    size: "lg",
    iconRight: "arrow-right",
    onClick: () => go("patterns")
  }, "Browse the library"))]), h("div", {
    key: "r",
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 14
    }
  }, [["layout-dashboard", "Layered navigation"], ["bar-chart-3", "Data visualization"], ["list-tree", "Expanding lists"], ["map", "Interactive maps"]].map((p, i) => h("div", {
    key: i,
    style: {
      background: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: "var(--rk-radius-md)",
      padding: 20,
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, [h(PatIcon, {
    key: "i",
    name: p[0]
  }), h("span", {
    key: "t",
    style: {
      fontFamily: "var(--rk-font-display)",
      fontWeight: 600,
      fontSize: 17,
      color: "#fff"
    }
  }, p[1])])))])),
  // CALLOUT
  h("section", {
    key: "cta",
    style: {
      padding: "80px 0"
    }
  }, h("div", {
    style: wrap
  }, h(Callout, {
    eyebrow: "Ready to cook?",
    title: "Let's turn your next report into something people use.",
    primaryLabel: "Contact the Kitchen",
    secondaryLabel: "See pricing",
    onClickPrimary: () => go("custom")
  }, "Tell us what you're publishing and we'll show you what's possible — no obligation, no reformatting.")))]);
}
function PatIcon({
  name
}) {
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  return h("i", {
    "data-lucide": name,
    width: 26,
    height: 26,
    style: {
      strokeWidth: 1.75,
      color: "var(--rk-macaroni-500)"
    }
  });
}
window.RKSite = window.RKSite || {};
window.RKSite.Home = Home;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Home.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Insights.jsx
try { (() => {
// Report Kitchen website — Insights (editorial section; sample articles)
const RKi = window.ReportKitchenDesignSystem_07c3a7;
const hi = React.createElement;
const RK_INSIGHTS = [{
  title: "Nobody reads your PDF. Here's the data.",
  cat: "Research",
  read: "6 min",
  dek: "We pulled analytics from 40 report launches. The drop-off between download and first page is worse than you think — and what to do about it.",
  color: "var(--rk-rhino-700)",
  icon: "line-chart",
  featured: true
}, {
  title: "Five information-design patterns every report should steal",
  cat: "Design",
  read: "8 min",
  dek: "From layered navigation to filterable data tables — the moves that turn a wall of text into something people actually explore.",
  color: "var(--rk-tomato-500)",
  icon: "layout-dashboard"
}, {
  title: "Using AI responsibly in nonprofit communications",
  cat: "AI",
  read: "7 min",
  dek: "Where large language models genuinely help with long-form content — and the guardrails we put in place before they touch a client's report.",
  color: "var(--rk-muffin)",
  icon: "sparkles"
}, {
  title: "Accessibility isn't a feature. It's the whole point.",
  cat: "Accessibility",
  read: "5 min",
  dek: "How we build to WCAG AA by default, and why an accessible report is almost always a more effective one.",
  color: "var(--rk-macaroni-600)",
  icon: "accessibility"
}, {
  title: "The 200-page problem: publishing comprehensive plans on the web",
  cat: "Case study",
  read: "9 min",
  dek: "Municipal comprehensive plans are massive. Here's how we make them navigable without losing an ounce of substance.",
  color: "var(--rk-rhino-500)",
  icon: "map"
}, {
  title: "Charts that earn their place",
  cat: "Data viz",
  read: "6 min",
  dek: "A field guide to choosing (and cutting) data visualizations so every chart in your report does real work.",
  color: "var(--rk-success)",
  icon: "bar-chart-3"
}];
function Insights({
  go
}) {
  const {
    Eyebrow,
    Callout
  } = RKi;
  const cats = ["All", "Design", "Research", "AI", "Accessibility", "Data viz", "Case study"];
  const [active, setActive] = React.useState("All");
  const wrap = {
    maxWidth: 1080,
    margin: "0 auto",
    padding: "0 40px"
  };
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  }, [active]);
  const dated = RK_INSIGHTS.map((a, i) => ({
    ...a,
    date: ["Jul 2, 2026", "Jun 18, 2026", "Jun 3, 2026", "May 21, 2026", "May 6, 2026", "Apr 22, 2026"][i]
  }));
  const shown = active === "All" ? dated : dated.filter(a => a.cat === active);
  return hi("div", null, [
  // HEAD
  hi("section", {
    key: "head",
    style: {
      padding: "60px 0 32px",
      borderBottom: "1px solid var(--rk-border)"
    }
  }, hi("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 14
    }
  }, [hi(Eyebrow, {
    key: "e"
  }, "Insights"), hi("h1", {
    key: "h",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 48,
      lineHeight: 1.04,
      letterSpacing: "-0.03em",
      color: "var(--rk-text-strong)",
      maxWidth: 760,
      textWrap: "balance"
    }
  }, "Ideas on reports, information design, and AI"), hi("p", {
    key: "p",
    style: {
      margin: 0,
      maxWidth: 620,
      fontFamily: "var(--rk-font-body)",
      fontSize: 18,
      lineHeight: 1.55,
      color: "var(--rk-text-muted)"
    }
  }, "Notes from the Kitchen on making long-form content more usable, accessible, and engaging.")])),
  // LIST + SIDEBAR
  hi("section", {
    key: "list",
    style: {
      padding: "40px 0 72px"
    }
  }, hi("div", {
    style: {
      ...wrap,
      display: "grid",
      gridTemplateColumns: "1fr 240px",
      gap: 56,
      alignItems: "start"
    }
  }, [
  // main column of posts
  hi("div", {
    key: "posts",
    style: {
      display: "flex",
      flexDirection: "column"
    }
  }, shown.map((a, i) => hi(PostRow, {
    key: a.title,
    a,
    first: i === 0
  }))),
  // sidebar
  hi("aside", {
    key: "side",
    style: {
      position: "sticky",
      top: 96,
      display: "flex",
      flexDirection: "column",
      gap: 28
    }
  }, [hi("div", {
    key: "topics",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 4
    }
  }, [hi("span", {
    key: "t",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: ".08em",
      color: "var(--rk-rhino-300)",
      marginBottom: 8
    }
  }, "Topics"), ...cats.map(c => hi("button", {
    key: c,
    onClick: () => setActive(c),
    style: {
      all: "unset",
      cursor: "pointer",
      padding: "7px 0",
      fontFamily: "var(--rk-font-body)",
      fontSize: 15,
      fontWeight: active === c ? 700 : 500,
      color: active === c ? "var(--rk-tomato-600)" : "var(--rk-text-body)",
      borderBottom: "1px solid var(--rk-border)"
    }
  }, c))]), hi("div", {
    key: "sub",
    style: {
      background: "var(--rk-rhino-700)",
      borderRadius: "var(--rk-radius-md)",
      padding: "20px 18px",
      display: "flex",
      flexDirection: "column",
      gap: 10
    }
  }, [hi("span", {
    key: "t",
    style: {
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 17,
      color: "#fff"
    }
  }, "Fresh from the oven"), hi("p", {
    key: "p",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 13.5,
      lineHeight: 1.5,
      color: "var(--rk-text-on-dark)",
      opacity: 0.85
    }
  }, "A short, occasional note when we publish something new."), hi("button", {
    key: "b",
    style: {
      all: "unset",
      cursor: "pointer",
      marginTop: 4,
      textAlign: "center",
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 14,
      color: "var(--rk-rhino-900)",
      background: "var(--rk-macaroni-500)",
      borderRadius: "var(--rk-radius-sm)",
      padding: "10px 14px"
    }
  }, "Subscribe")])])]))]);
}
function PostRow({
  a,
  first
}) {
  const [hover, setHover] = React.useState(false);
  return hi("a", {
    href: "#",
    onClick: e => e.preventDefault(),
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 9,
      padding: "26px 0",
      textDecoration: "none",
      borderTop: first ? "none" : "1px solid var(--rk-border)"
    }
  }, [hi("div", {
    key: "m",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      fontFamily: "var(--rk-font-body)",
      fontSize: 13
    }
  }, [hi("span", {
    key: "c",
    style: {
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: ".06em",
      color: "var(--rk-tomato)"
    }
  }, a.cat), hi("span", {
    key: "d1",
    style: {
      color: "var(--rk-rhino-200)"
    }
  }, "·"), hi("span", {
    key: "dt",
    style: {
      color: "var(--rk-text-muted)",
      fontWeight: 500
    }
  }, a.date), hi("span", {
    key: "d2",
    style: {
      color: "var(--rk-rhino-200)"
    }
  }, "·"), hi("span", {
    key: "r",
    style: {
      color: "var(--rk-text-muted)",
      fontWeight: 500
    }
  }, a.read + " read")]), hi("h2", {
    key: "h",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 27,
      lineHeight: 1.12,
      letterSpacing: "-0.02em",
      color: hover ? "var(--rk-tomato-600)" : "var(--rk-text-strong)",
      transition: "color var(--rk-dur)",
      maxWidth: 640
    }
  }, a.title), hi("p", {
    key: "dek",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 16.5,
      lineHeight: 1.6,
      color: "var(--rk-text-muted)",
      maxWidth: 620
    }
  }, a.dek), hi("span", {
    key: "link",
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      marginTop: 2,
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 14.5,
      color: "var(--rk-tomato-600)"
    }
  }, ["Read more", hi("i", {
    key: "i",
    "data-lucide": "arrow-right",
    width: 16,
    height: 16,
    style: {
      strokeWidth: 2.25,
      transform: hover ? "translateX(3px)" : "none",
      transition: "transform var(--rk-dur)"
    }
  })])]);
}
window.RKSite = window.RKSite || {};
window.RKSite.Insights = Insights;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Insights.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/OfferingCustom.jsx
try { (() => {
// Report Kitchen website — Report Kitchen Custom (offering page)
const RKc = window.ReportKitchenDesignSystem_07c3a7;
const hc = React.createElement;
function OfferingCustom({
  go
}) {
  const {
    Button,
    Badge,
    SectionHeading,
    Callout,
    Card,
    FeatureCard
  } = RKc;
  const wrap = {
    maxWidth: 1120,
    margin: "0 auto",
    padding: "0 40px"
  };
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const process = [{
    icon: "upload",
    t: "Share your PDF",
    b: "Send us the report, plan or toolkit you've already published."
  }, {
    icon: "pencil-ruler",
    t: "We design the experience",
    b: "Information architecture, navigation and layouts tailored to your content."
  }, {
    icon: "cooking-pot",
    t: "We build it",
    b: "A bespoke, responsive, accessible site — charts, media and interactions included."
  }, {
    icon: "rocket",
    t: "Launch & measure",
    b: "We publish, hand off, and set you up with engagement analytics."
  }];
  return hc("div", null, [
  // hero
  hc("section", {
    key: "hero",
    style: {
      background: "var(--rk-rhino-700)",
      padding: "72px 0 80px",
      color: "#fff"
    }
  }, hc("div", {
    style: {
      ...wrap,
      display: "grid",
      gridTemplateColumns: "1.1fr 0.9fr",
      gap: 48,
      alignItems: "center"
    }
  }, [hc("div", {
    key: "l",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 22
    }
  }, [hc(Badge, {
    key: "b",
    tone: "success",
    dot: true
  }, "Available now · Our flagship"), hc("h1", {
    key: "h",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 58,
      lineHeight: 1.02,
      letterSpacing: "-0.03em",
      textWrap: "balance"
    }
  }, "Report Kitchen Custom"), hc("p", {
    key: "p",
    style: {
      margin: 0,
      maxWidth: 520,
      fontFamily: "var(--rk-font-body)",
      fontSize: 20,
      lineHeight: 1.55,
      color: "var(--rk-text-on-dark)"
    }
  }, "The full white-glove build. Hand us your PDF and we'll cook up a bespoke, responsive, accessible website — start to finish."), hc("div", {
    key: "cta",
    style: {
      display: "flex",
      gap: 12,
      marginTop: 4
    }
  }, [hc(Button, {
    key: "a",
    variant: "accent",
    size: "lg",
    iconRight: "arrow-right",
    onClick: () => go("custom")
  }, "Contact the Kitchen"), hc(Button, {
    key: "b",
    variant: "ghost",
    size: "lg",
    style: {
      color: "#fff"
    },
    onClick: () => go("work")
  }, "See examples")])]), hc("div", {
    key: "r",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, [["chef-hat", "Done for you, end to end"], ["accessibility", "Accessible by default (WCAG AA)"], ["smartphone", "Fully responsive on every device"], ["line-chart", "Reader engagement analytics"]].map((v, i) => hc("div", {
    key: i,
    style: {
      display: "flex",
      alignItems: "center",
      gap: 14,
      background: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: "var(--rk-radius-md)",
      padding: "16px 18px"
    }
  }, [hc("i", {
    key: "i",
    "data-lucide": v[0],
    width: 24,
    height: 24,
    style: {
      strokeWidth: 2,
      color: "var(--rk-macaroni-500)",
      flexShrink: 0
    }
  }), hc("span", {
    key: "t",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 600,
      fontSize: 16.5
    }
  }, v[1])])))])),
  // process
  hc("section", {
    key: "proc",
    style: {
      padding: "80px 0"
    }
  }, hc("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 44
    }
  }, [hc(SectionHeading, {
    key: "sh",
    align: "center",
    eyebrow: "How it works",
    title: "From PDF to launch in four steps"
  }), hc("div", {
    key: "g",
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 20
    }
  }, process.map((p, i) => hc("div", {
    key: i,
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 12,
      padding: 24,
      background: "var(--rk-surface-card)",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-lg)"
    }
  }, [hc("div", {
    key: "top",
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, [hc("div", {
    key: "ic",
    style: {
      width: 46,
      height: 46,
      borderRadius: "var(--rk-radius-md)",
      background: "var(--rk-tomato-100)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, hc("i", {
    "data-lucide": p.icon,
    width: 23,
    height: 23,
    style: {
      strokeWidth: 2,
      color: "var(--rk-tomato-600)"
    }
  })), hc("span", {
    key: "n",
    style: {
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 30,
      color: "var(--rk-rhino-100)"
    }
  }, "0" + (i + 1))]), hc("h3", {
    key: "t",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 19,
      color: "var(--rk-text-strong)"
    }
  }, p.t), hc("p", {
    key: "b",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 15,
      lineHeight: 1.55,
      color: "var(--rk-text-muted)"
    }
  }, p.b)])))])),
  // samples
  hc("section", {
    key: "samp",
    style: {
      background: "var(--rk-cream)",
      padding: "80px 0",
      borderTop: "1px solid var(--rk-border)",
      borderBottom: "1px solid var(--rk-border)"
    }
  }, hc("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 36
    }
  }, [hc(SectionHeading, {
    key: "sh",
    eyebrow: "Recently plated",
    title: "A few we've built"
  }), hc("div", {
    key: "g",
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 22
    }
  }, [hc(Card, {
    key: "1",
    client: "Enterprise Community Partners",
    title: "Housing2Justice Toolkit",
    description: "80 pages, a legal survey and a provider database — one interactive site.",
    coverColor: "var(--rk-rhino-700)",
    coverIcon: "scale",
    coverText: "Toolkit",
    tags: ["Housing"],
    onClick: () => go("profile")
  }), hc(Card, {
    key: "2",
    client: "Charles Stewart Mott Foundation",
    title: "Focus on Flint",
    description: "Dozens of charts and infographics, fully responsive and shareable.",
    coverColor: "var(--rk-muffin)",
    coverIcon: "bar-chart-3",
    coverText: "Report",
    tags: ["Data"],
    onClick: () => go("profile")
  }), hc(Card, {
    key: "3",
    client: "Enterprise Community Partners",
    title: "Keep Safe Manual",
    description: "A 500+ page resilient-housing manual, made easy to navigate.",
    coverColor: "var(--rk-macaroni-600)",
    coverIcon: "life-buoy",
    coverText: "Manual",
    tags: ["Climate"],
    onClick: () => go("profile")
  })])])),
  // callout
  hc("section", {
    key: "cta",
    style: {
      padding: "80px 0"
    }
  }, hc("div", {
    style: wrap
  }, hc(Callout, {
    eyebrow: "Let's talk",
    title: "Tell us about your report — we'll show you what's possible.",
    primaryLabel: "Contact the Kitchen",
    secondaryLabel: "Explore all offerings",
    onClickSecondary: () => go("home")
  }, "Every custom build starts with a conversation. No obligation, no reformatting on your end.")))]);
}
window.RKSite = window.RKSite || {};
window.RKSite.OfferingCustom = OfferingCustom;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/OfferingCustom.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/OurWork.jsx
try { (() => {
// Report Kitchen website — Our Work grid
const RKw = window.ReportKitchenDesignSystem_07c3a7;
const hw = React.createElement;
const RK_PROJECTS = [{
  title: "Green Communities 2026",
  client: "Enterprise Community Partners",
  desc: "Interactive certification guide helps affordable housing teams navigate sustainable building requirements.",
  color: "var(--rk-success)",
  icon: "leaf",
  kind: "Guide",
  cat: "Housing"
}, {
  title: "Housing2Justice National Toolkit",
  client: "Enterprise Community Partners",
  desc: "Helping the housing industry better understand and serve the justice-impacted population.",
  color: "var(--rk-rhino-700)",
  icon: "scale",
  kind: "Toolkit",
  cat: "Housing"
}, {
  title: "Climate Smart Housing",
  client: "Enterprise Community Partners",
  desc: "Driving climate improvements into low- and moderate-income communities.",
  color: "var(--rk-muffin)",
  icon: "cloud-sun",
  kind: "Report",
  cat: "Climate"
}, {
  title: "Social Housing in Vienna",
  client: "LA Housing Leaders",
  desc: "Reflections from Los Angeles housing leaders on Vienna's social housing model.",
  color: "var(--rk-tomato-500)",
  icon: "building-2",
  kind: "Report",
  cat: "Housing"
}, {
  title: "Anchor Collaboratives Playbook",
  client: "Democracy Collaborative",
  desc: "A digital playbook for advancing equitable economic development and wealth building.",
  color: "var(--rk-rhino-500)",
  icon: "book-open",
  kind: "Playbook",
  cat: "Economy"
}, {
  title: "Climate Safe Housing",
  client: "Enterprise Community Partners",
  desc: "Strategies to protect multifamily buildings against extreme weather and build resilient communities.",
  color: "var(--rk-macaroni-600)",
  icon: "shield",
  kind: "Toolkit",
  cat: "Climate"
}, {
  title: "Trauma-Informed Housing",
  client: "Enterprise Community Partners",
  desc: "A toolkit for advancing equity and economic opportunity in affordable housing.",
  color: "var(--rk-muffin)",
  icon: "heart-handshake",
  kind: "Toolkit",
  cat: "Housing"
}, {
  title: "Whole Child Policy Toolkit",
  client: "Learning Policy Institute",
  desc: "Evidence-based strategies and resources to advance whole-child policy and systems change.",
  color: "var(--rk-tomato-500)",
  icon: "graduation-cap",
  kind: "Toolkit",
  cat: "Education"
}, {
  title: "FOIA Basics for Activists",
  client: "Center for Constitutional Rights",
  desc: "A resource for activists with tools and advice for successful FOIA requests.",
  color: "var(--rk-rhino-700)",
  icon: "file-search",
  kind: "Guide",
  cat: "Policy"
}, {
  title: "Restarting & Reinventing School",
  client: "Learning Policy Institute",
  desc: "A framework to reimagine schooling using safe, equitable, student-centered approaches.",
  color: "var(--rk-macaroni-600)",
  icon: "school",
  kind: "Framework",
  cat: "Education"
}, {
  title: "Keep Safe Manual",
  client: "Enterprise Community Partners",
  desc: "A 500+ page resource for resilient housing design in island communities, made easy to navigate.",
  color: "var(--rk-rhino-500)",
  icon: "life-buoy",
  kind: "Manual",
  cat: "Climate"
}, {
  title: "Enterprise Green Communities",
  client: "Enterprise Community Partners",
  desc: "The certification framework for sustainable affordable housing — free of the old PDF format.",
  color: "var(--rk-success)",
  icon: "leaf",
  kind: "Criteria",
  cat: "Housing"
}, {
  title: "ALEC Attacks",
  client: "Center for Constitutional Rights",
  desc: "A report exposing the tactics of a secretive corporate lobbying group.",
  color: "var(--rk-tomato-600)",
  icon: "megaphone",
  kind: "Report",
  cat: "Policy"
}, {
  title: "Focus on Flint",
  client: "Charles Stewart Mott Foundation",
  desc: "Dozens of charts and infographics across eight issues affecting the Flint community.",
  color: "var(--rk-muffin)",
  icon: "bar-chart-3",
  kind: "Report",
  cat: "Data"
}, {
  title: "Public Attitudes Towards Gifted Education",
  client: "Institute for Educational Advancement",
  desc: "Findings from a broad survey of American attitudes towards gifted education.",
  color: "var(--rk-rhino-700)",
  icon: "clipboard-list",
  kind: "Survey",
  cat: "Education"
}, {
  title: "Elements of Success",
  client: "Housing Authority Partnership",
  desc: "Best-practices review with video interviews woven seamlessly into the reader experience.",
  color: "var(--rk-macaroni-600)",
  icon: "video",
  kind: "Review",
  cat: "Housing"
}];
function OurWork({
  go
}) {
  const cats = ["All", "Housing", "Education", "Climate", "Policy", "Economy", "Data"];
  const [active, setActive] = React.useState("All");
  const {
    Card,
    Tag,
    Eyebrow
  } = RKw;
  const wrap = {
    maxWidth: 1200,
    margin: "0 auto",
    padding: "0 40px"
  };
  const shown = active === "All" ? RK_PROJECTS : RK_PROJECTS.filter(p => p.cat === active);
  return hw("div", null, [hw("section", {
    key: "head",
    style: {
      background: "var(--rk-cream)",
      padding: "64px 0 56px",
      borderBottom: "1px solid var(--rk-border)"
    }
  }, hw("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 18
    }
  }, [hw(Eyebrow, {
    key: "e"
  }, "Our Work"), hw("h1", {
    key: "h",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 54,
      lineHeight: 1.03,
      letterSpacing: "-0.03em",
      color: "var(--rk-text-strong)",
      maxWidth: 820,
      textWrap: "balance"
    }
  }, "Reports, toolkits and plans — reinvented as living websites."), hw("p", {
    key: "p",
    style: {
      margin: 0,
      maxWidth: 640,
      fontFamily: "var(--rk-font-body)",
      fontSize: 19,
      lineHeight: 1.55,
      color: "var(--rk-text-muted)"
    }
  }, "A taste of what happens when long-form content breaks free of the PDF. Browse by focus area.")])), hw("section", {
    key: "grid",
    style: {
      padding: "40px 0 88px"
    }
  }, hw("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 32
    }
  }, [hw("div", {
    key: "filters",
    style: {
      display: "flex",
      gap: 8,
      flexWrap: "wrap"
    }
  }, cats.map(c => hw(Tag, {
    key: c,
    interactive: true,
    active: active === c,
    onClick: () => setActive(c)
  }, c))), hw("div", {
    key: "g",
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 22
    }
  }, shown.map((p, i) => hw(Card, {
    key: i,
    client: p.client,
    title: p.title,
    description: p.desc,
    coverColor: p.color,
    coverIcon: p.icon,
    coverText: p.kind,
    tags: [p.cat],
    onClick: () => go("profile")
  })))]))]);
}
window.RKSite = window.RKSite || {};
window.RKSite.OurWork = OurWork;
window.RK_PROJECTS = RK_PROJECTS;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/OurWork.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/PatternLibrary.jsx
try { (() => {
// Report Kitchen website — Info Design Pattern Library
const RKl = window.ReportKitchenDesignSystem_07c3a7;
const hl = React.createElement;
const RK_PATTERNS = [{
  icon: "layout-dashboard",
  name: "Layered navigation",
  cat: "Navigation",
  desc: "Reveal depth on demand with accordions, tabs and expanding sections so readers scan first, dive second.",
  when: "Long documents with clear hierarchy."
}, {
  icon: "bar-chart-3",
  name: "Data visualization",
  cat: "Data",
  desc: "Turn tables of numbers into charts readers can actually interpret at a glance.",
  when: "Reports built on survey or statistical data."
}, {
  icon: "list-tree",
  name: "Expanding lists",
  cat: "Navigation",
  desc: "Progressive disclosure for long reference lists — summaries up top, detail on click.",
  when: "Directories, glossaries, recommendations."
}, {
  icon: "map",
  name: "Interactive maps",
  cat: "Geography",
  desc: "Let readers explore place-based data by region instead of scrolling static images.",
  when: "Geographic or jurisdictional content."
}, {
  icon: "sliders-horizontal",
  name: "Filter & search",
  cat: "Data",
  desc: "Give readers controls to narrow large datasets to what's relevant to them.",
  when: "Databases and large tables."
}, {
  icon: "quote",
  name: "Pull quotes & callouts",
  cat: "Editorial",
  desc: "Surface the most memorable lines and key takeaways as designed moments.",
  when: "Narrative-heavy reports."
}, {
  icon: "table-2",
  name: "Responsive tables",
  cat: "Data",
  desc: "Tables that reflow gracefully on phones instead of forcing a pinch-and-zoom.",
  when: "Any content with tabular data."
}, {
  icon: "milestone",
  name: "Timelines",
  cat: "Editorial",
  desc: "Sequence events or process steps as a scannable visual path.",
  when: "History, roadmaps, multi-phase plans."
}, {
  icon: "video",
  name: "Embedded media",
  cat: "Media",
  desc: "Weave video and audio into the reading flow — no awkward external links.",
  when: "Interviews and multimedia projects."
}];
function PatternLibrary({
  go
}) {
  const {
    Tag,
    Eyebrow,
    Callout
  } = RKl;
  const cats = ["All", "Navigation", "Data", "Editorial", "Media", "Geography"];
  const [active, setActive] = React.useState("All");
  const wrap = {
    maxWidth: 1160,
    margin: "0 auto",
    padding: "0 40px"
  };
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  }, [active]);
  const shown = active === "All" ? RK_PATTERNS : RK_PATTERNS.filter(p => p.cat === active);
  return hl("div", null, [hl("section", {
    key: "head",
    style: {
      padding: "64px 0 48px"
    }
  }, hl("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 18,
      alignItems: "center",
      textAlign: "center"
    }
  }, [hl(Eyebrow, {
    key: "e",
    color: "macaroni"
  }, "Free resource · Content marketing"), hl("h1", {
    key: "h",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 56,
      lineHeight: 1.02,
      letterSpacing: "-0.03em",
      color: "var(--rk-text-strong)",
      maxWidth: 820,
      textWrap: "balance"
    }
  }, "The Info Design Pattern Library"), hl("p", {
    key: "p",
    style: {
      margin: 0,
      maxWidth: 640,
      fontFamily: "var(--rk-font-body)",
      fontSize: 19,
      lineHeight: 1.55,
      color: "var(--rk-text-muted)"
    }
  }, "A growing, open library of information-design patterns for long-form content — what each one is, when to use it, and how to build it.")])), hl("section", {
    key: "grid",
    style: {
      padding: "0 0 80px"
    }
  }, hl("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 28
    }
  }, [hl("div", {
    key: "f",
    style: {
      display: "flex",
      gap: 8,
      flexWrap: "wrap",
      justifyContent: "center"
    }
  }, cats.map(c => hl(Tag, {
    key: c,
    interactive: true,
    active: active === c,
    onClick: () => setActive(c)
  }, c))), hl("div", {
    key: "g",
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 20
    }
  }, shown.map((p, i) => hl(PatternCard, {
    key: p.name,
    p
  })))])), hl("section", {
    key: "cta",
    style: {
      padding: "0 0 88px"
    }
  }, hl("div", {
    style: wrap
  }, hl(Callout, {
    tone: "cream",
    eyebrow: "Want a hand?",
    title: "Not sure which pattern fits your report?",
    primaryLabel: "Talk to the Kitchen",
    secondaryLabel: "See our work",
    onClickSecondary: () => go("work")
  }, "We use these patterns every day. Tell us about your content and we'll recommend the right approach.")))]);
}
function PatternCard({
  p
}) {
  const [hover, setHover] = React.useState(false);
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  return hl("div", {
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 14,
      padding: 26,
      background: "var(--rk-surface-card)",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-lg)",
      boxShadow: hover ? "var(--rk-shadow-md)" : "none",
      transform: hover ? "translateY(-3px)" : "none",
      transition: "transform var(--rk-dur) var(--rk-ease-out), box-shadow var(--rk-dur)"
    }
  }, [hl("div", {
    key: "top",
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, [hl("div", {
    key: "ic",
    style: {
      width: 50,
      height: 50,
      borderRadius: "var(--rk-radius-md)",
      background: "var(--rk-macaroni-100)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }
  }, hl("i", {
    "data-lucide": p.icon,
    width: 25,
    height: 25,
    style: {
      strokeWidth: 1.9,
      color: "var(--rk-macaroni-600)"
    }
  })), hl("span", {
    key: "c",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 600,
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: ".06em",
      color: "var(--rk-rhino-300)"
    }
  }, p.cat)]), hl("h3", {
    key: "t",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 21,
      letterSpacing: "-0.01em",
      color: "var(--rk-text-strong)"
    }
  }, p.name), hl("p", {
    key: "d",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 15,
      lineHeight: 1.55,
      color: "var(--rk-text-muted)"
    }
  }, p.desc), hl("div", {
    key: "w",
    style: {
      marginTop: "auto",
      paddingTop: 12,
      borderTop: "1px dashed var(--rk-border-strong)",
      display: "flex",
      gap: 8,
      alignItems: "baseline"
    }
  }, [hl("span", {
    key: "l",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 12.5,
      textTransform: "uppercase",
      letterSpacing: ".05em",
      color: "var(--rk-tomato)"
    }
  }, "When"), hl("span", {
    key: "v",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 14,
      color: "var(--rk-text-body)"
    }
  }, p.when)])]);
}
window.RKSite = window.RKSite || {};
window.RKSite.PatternLibrary = PatternLibrary;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/PatternLibrary.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/ProjectProfile.jsx
try { (() => {
// Report Kitchen website — Project Profile (Housing2Justice)
const RKp = window.ReportKitchenDesignSystem_07c3a7;
const hp = React.createElement;
function BeforeAfter() {
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const line = (w, c, k) => hp("div", {
    key: k,
    style: {
      height: 6,
      width: w,
      borderRadius: 4,
      background: c
    }
  });
  const panel = (label, tone) => hp("div", {
    style: {
      flex: 1,
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, [hp("span", {
    key: "l",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: ".07em",
      color: tone === "before" ? "var(--rk-text-muted)" : "var(--rk-tomato)"
    }
  }, label), tone === "before" ? hp("div", {
    key: "c",
    style: {
      background: "#fff",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-sm)",
      padding: 22,
      display: "flex",
      flexDirection: "column",
      gap: 9,
      opacity: 0.75
    }
  }, [line("60%", "var(--rk-rhino-300)", "a"), line("100%", "var(--rk-rhino-100)", "b"), line("95%", "var(--rk-rhino-100)", "c"), line("100%", "var(--rk-rhino-100)", "d"), line("80%", "var(--rk-rhino-100)", "e"), line("100%", "var(--rk-rhino-100)", "f"), line("55%", "var(--rk-rhino-100)", "g")]) : hp("div", {
    key: "c",
    style: {
      background: "#fff",
      border: "1px solid var(--rk-border)",
      borderRadius: "var(--rk-radius-md)",
      overflow: "hidden",
      boxShadow: "var(--rk-shadow-md)"
    }
  }, [hp("div", {
    key: "b",
    style: {
      background: "var(--rk-rhino-700)",
      padding: "16px 18px",
      display: "flex",
      flexDirection: "column",
      gap: 7
    }
  }, [line("50%", "var(--rk-macaroni-500)", "a"), line("78%", "rgba(255,255,255,0.8)", "b")]), hp("div", {
    key: "body",
    style: {
      padding: 18,
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 10
    }
  }, [hp("div", {
    key: "x",
    style: {
      gridColumn: "1 / -1",
      height: 40,
      borderRadius: 8,
      background: "var(--rk-macaroni-100)",
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "0 12px"
    }
  }, [hp("i", {
    key: "i",
    "data-lucide": "list-tree",
    width: 18,
    height: 18,
    style: {
      color: "var(--rk-macaroni-600)"
    }
  }), line("60%", "var(--rk-macaroni-300)", "ln")]), hp("div", {
    key: "a",
    style: {
      height: 34,
      borderRadius: 6,
      background: "var(--rk-gray-100)"
    }
  }), hp("div", {
    key: "c2",
    style: {
      height: 34,
      borderRadius: 6,
      background: "var(--rk-gray-100)"
    }
  })])])]);
  return hp("div", {
    style: {
      display: "flex",
      gap: 28,
      alignItems: "stretch"
    }
  }, [hp("div", {
    key: "b",
    style: {
      flex: 1
    }
  }, panel("Before: static PDF", "before")), hp("div", {
    key: "arr",
    style: {
      display: "flex",
      alignItems: "center"
    }
  }, hp("i", {
    "data-lucide": "arrow-right",
    width: 28,
    height: 28,
    style: {
      strokeWidth: 2.5,
      color: "var(--rk-tomato-500)"
    }
  })), hp("div", {
    key: "a",
    style: {
      flex: 1
    }
  }, panel("After: interactive site", "after"))]);
}
function ProjectProfile({
  go
}) {
  const {
    Button,
    Badge,
    Accordion,
    Callout,
    Tag
  } = RKp;
  const wrap = {
    maxWidth: 1080,
    margin: "0 auto",
    padding: "0 40px"
  };
  React.useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  const stat = (n, l) => hp("div", {
    key: l,
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 4
    }
  }, [hp("span", {
    key: "n",
    style: {
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 42,
      color: "var(--rk-tomato-500)",
      letterSpacing: "-0.02em"
    }
  }, n), hp("span", {
    key: "l",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontSize: 15,
      color: "var(--rk-text-muted)"
    }
  }, l)]);
  return hp("div", null, [
  // back
  hp("div", {
    key: "back",
    style: {
      ...wrap,
      paddingTop: 28
    }
  }, hp("button", {
    onClick: () => go("work"),
    style: {
      all: "unset",
      cursor: "pointer",
      display: "inline-flex",
      alignItems: "center",
      gap: 7,
      fontFamily: "var(--rk-font-body)",
      fontWeight: 600,
      fontSize: 15,
      color: "var(--rk-text-muted)"
    }
  }, [hp("i", {
    key: "i",
    "data-lucide": "arrow-left",
    width: 17,
    height: 17,
    style: {
      strokeWidth: 2.25
    }
  }), "All work"])),
  // hero
  hp("section", {
    key: "hero",
    style: {
      padding: "32px 0 56px"
    }
  }, hp("div", {
    style: {
      ...wrap,
      display: "flex",
      flexDirection: "column",
      gap: 22
    }
  }, [hp("div", {
    key: "tags",
    style: {
      display: "flex",
      gap: 8
    }
  }, [hp(Tag, {
    key: "1",
    tone: "tomato"
  }, "Housing"), hp(Tag, {
    key: "2",
    tone: "muffin"
  }, "Toolkit")]), hp("span", {
    key: "cl",
    style: {
      fontFamily: "var(--rk-font-body)",
      fontWeight: 700,
      fontSize: 15,
      color: "var(--rk-text-muted)"
    }
  }, "Enterprise Community Partners"), hp("h1", {
    key: "h",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 800,
      fontSize: 56,
      lineHeight: 1.02,
      letterSpacing: "-0.03em",
      color: "var(--rk-text-strong)",
      maxWidth: 860,
      textWrap: "balance"
    }
  }, "Housing as a pathway to justice"), hp("p", {
    key: "p",
    style: {
      margin: 0,
      maxWidth: 680,
      fontFamily: "var(--rk-font-body)",
      fontSize: 20,
      lineHeight: 1.55,
      color: "var(--rk-text-muted)"
    }
  }, "Helping the housing industry better understand and serve the justice-impacted population — through an interactive national toolkit."), hp("div", {
    key: "cta",
    style: {
      display: "flex",
      gap: 12,
      marginTop: 4
    }
  }, [hp(Button, {
    key: "a",
    iconRight: "external-link"
  }, "Visit the site"), hp(Button, {
    key: "b",
    variant: "secondary",
    onClick: () => go("custom")
  }, "Start a project like this")])])),
  // before/after
  hp("section", {
    key: "ba",
    style: {
      background: "var(--rk-cream)",
      padding: "64px 0",
      borderTop: "1px solid var(--rk-border)",
      borderBottom: "1px solid var(--rk-border)"
    }
  }, hp("div", {
    style: wrap
  }, hp(BeforeAfter))),
  // stats + narrative
  hp("section", {
    key: "body",
    style: {
      padding: "64px 0"
    }
  }, hp("div", {
    style: {
      ...wrap,
      display: "grid",
      gridTemplateColumns: "1fr 1.2fr",
      gap: 56,
      alignItems: "start"
    }
  }, [hp("div", {
    key: "stats",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 32
    }
  }, [stat("80+", "pages of narrative content"), stat("50", "states of legal survey data"), stat("1", "searchable provider database"), stat("100%", "WCAG AA accessible")]), hp("div", {
    key: "narr",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 20
    }
  }, [hp("h2", {
    key: "t",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-display)",
      fontWeight: 700,
      fontSize: 32,
      letterSpacing: "-0.02em",
      color: "var(--rk-text-strong)"
    }
  }, "The recipe"), hp("p", {
    key: "p1",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 18,
      lineHeight: 1.65,
      color: "var(--rk-text-body)"
    }
  }, "We combined 80 pages of narrative content, a spreadsheet survey of state and local laws, and a database of service providers into a single interactive toolkit."), hp("p", {
    key: "p2",
    style: {
      margin: 0,
      fontFamily: "var(--rk-font-body)",
      fontSize: 18,
      lineHeight: 1.65,
      color: "var(--rk-text-body)"
    }
  }, "Layered content lets readers navigate, scan and filter to reach the most relevant material quickly. And as with every Report Kitchen site, admins get full analytics on what readers actually engage with — from accordions to expanding lists."), hp("div", {
    key: "acc",
    style: {
      marginTop: 8
    }
  }, hp(Accordion, {
    items: [{
      q: "Layered navigation",
      a: "Accordions, modals and expanding lists keep a dense toolkit scannable without hiding depth."
    }, {
      q: "Filterable law database",
      a: "Readers filter state and local laws to their jurisdiction in seconds."
    }, {
      q: "Engagement analytics",
      a: "Site admins see exactly which sections and interactions readers open."
    }]
  }))])])),
  // callout
  hp("section", {
    key: "cta",
    style: {
      padding: "0 0 88px"
    }
  }, hp("div", {
    style: wrap
  }, hp(Callout, {
    tone: "tomato",
    eyebrow: "Your turn",
    title: "Does your organization produce toolkits or resource guides?",
    primaryLabel: "Get in touch",
    secondaryLabel: "See more work",
    onClickSecondary: () => go("work")
  }, "How much more engaging would they be if visitors could truly interact with your content instead of just downloading a PDF?")))]);
}
window.RKSite = window.RKSite || {};
window.RKSite.ProjectProfile = ProjectProfile;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/ProjectProfile.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Eyebrow = __ds_scope.Eyebrow;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.Link = __ds_scope.Link;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Textarea = __ds_scope.Textarea;

__ds_ns.Accordion = __ds_scope.Accordion;

__ds_ns.Callout = __ds_scope.Callout;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.FeatureCard = __ds_scope.FeatureCard;

__ds_ns.SectionHeading = __ds_scope.SectionHeading;

})();
