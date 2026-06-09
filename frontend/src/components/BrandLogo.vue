<script setup>
// alpha brand mark — the README's geodesic globe: an orthographically projected
// frequency-2 icosphere (front-facing edges only), one teal-filled facet at the
// upper left, and a teal equatorial line running through the sphere.
// Path data is pre-baked from the icosphere projection so it ships as a tiny
// static SVG; mesh strokes use currentColor so the mark adapts to the theme.
defineProps({ size: { type: Number, default: 34 } })

const MESH =
  'M16.8 10.3L13.1 22.2M13.1 22.2L27.5 12.8M16.8 10.3L27.5 12.8M14.9 37L13.1 22.2' +
  'M14.9 37L26.4 28.5M13.1 22.2L26.4 28.5M26.4 28.5L27.5 12.8M39.5 21.1L26.4 28.5' +
  'M39.5 21.1L27.5 12.8M27.5 12.8L30.3 4.5M16.8 10.3L30.3 4.5M39.5 21.1L43.7 10.8' +
  'M27.5 12.8L43.7 10.8M43.7 10.8L30.3 4.5M44.3 6.9L43.7 10.8M44.3 6.9L30.3 4.5' +
  'M30.3 4.5L17.6 8.7M16.8 10.3L17.6 8.7M17.6 8.7L7 19.6M16.8 10.3L7 19.6' +
  'M13.1 22.2L7 19.6M4.6 32.6L7 19.6M4.6 32.6L5.8 35.3M7 19.6L5.8 35.3' +
  'M13.1 22.2L5.8 35.3M14.9 37L5.8 35.3M43.7 10.8L55.4 16.9M44.3 6.9L55.4 16.9' +
  'M39.5 21.1L52.5 25.2M43.7 10.8L52.5 25.2M52.5 25.2L55.4 16.9M59.4 31.4L52.5 25.2' +
  'M59.4 31.4L55.4 16.9M26.4 28.5L41.9 36.1M39.5 21.1L41.9 36.1M14.9 37L27.4 45.5' +
  'M26.4 28.5L27.4 45.5M27.4 45.5L41.9 36.1M41.3 50L27.4 45.5M41.3 50L41.9 36.1' +
  'M5.8 35.3L14.7 49.7M14.9 37L14.7 49.7M4.6 32.6L8.6 47.1M5.8 35.3L8.6 47.1' +
  'M8.6 47.1L14.7 49.7M19.7 57.1L8.6 47.1M19.7 57.1L14.7 49.7M59.4 31.4L57 44.4' +
  'M59.4 31.4L53.6 42.2M57 44.4L53.6 42.2M53.6 42.2L46.4 55.3M41.3 50L53.6 42.2' +
  'M41.3 50L46.4 55.3M57 44.4L46.4 55.3M41.3 50L30.2 57.3M46.4 55.3L30.2 57.3' +
  'M30.2 57.3L33.7 59.5M19.7 57.1L30.2 57.3M19.7 57.1L33.7 59.5M46.4 55.3L33.7 59.5' +
  'M41.9 36.1L53.6 42.2M52.5 25.2L53.6 42.2M52.5 25.2L41.9 36.1M14.7 49.7L30.2 57.3' +
  'M27.4 45.5L30.2 57.3M27.4 45.5L14.7 49.7'
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 64 64"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <polygon class="facet" points="13.1,22.2 26.4,28.5 27.5,12.8" />
    <path class="mesh" :d="MESH" />
    <line class="equator" x1="1.5" y1="32" x2="62.5" y2="32" />
  </svg>
</template>

<style scoped>
.facet {
  fill: var(--accent);
  opacity: 0.92;
}
.mesh {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.62;
}
.equator {
  stroke: var(--accent);
  stroke-width: 1.9;
  stroke-linecap: round;
  opacity: 0.9;
}
</style>
