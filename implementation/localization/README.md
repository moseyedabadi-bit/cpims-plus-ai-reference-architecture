# Persian (`fa-IR`) localization overlay

The Primero project already contains a large Dari (`fa-AF`) locale and RTL support. This overlay uses that complete upstream locale as the structural baseline, keeps the same translation keys, and produces an Iranian-Persian `fa-IR` locale.

## Why not hand-copy a translation snapshot?

A generated overlay is easier to audit and update. Every release can be rebuilt from a pinned upstream Primero tag, key coverage can be compared automatically, and terminology changes remain reviewable.

## Build

```bash
ruby implementation/localization/build_fa_ir.rb \
  --upstream ./primero-v2.14.5 \
  --output ./build/fa-ir
```

The builder validates the Git blob SHA of the two translation sources from Primero v2.14.5 before generating output. If upstream changes unexpectedly, generation fails closed.

## Apply

```bash
ruby implementation/localization/apply_to_primero.rb \
  --primero ./primero-v2.14.5 \
  --generated ./build/fa-ir
```

The patcher:

- copies `config/locales/fa-IR.yml`;
- copies `config/locales/dates/fa-IR.yml`;
- adds `fa-IR` to `LOCALES`;
- adds `fa-IR` to `RTL_LOCALES`;
- adds `fa-IR -> fa-AF -> en` fallback;
- adds `fa-IR` to the front-end RTL switch.

It checks known anchors and aborts when the expected Primero source structure is not present.

## QA

```bash
ruby implementation/localization/qa_locale.rb \
  --primero ./primero-v2.14.5 \
  --generated ./build/fa-ir
```

The QA script verifies complete leaf-key coverage and prints remaining terminology candidates that should receive human review.

## Important limitation

"Complete localization" here means **complete upstream translation-key coverage**, not a claim that every term has already passed professional Iranian child-protection/legal/medical language review. Such review remains a production gate.

## Calendar

The overlay localizes Gregorian month names into Persian but intentionally does not change Primero's canonical stored date/calendar semantics. Jalali display can be considered later as a presentation-only feature after interoperability and date-boundary testing.
