// alpha — animated number composable.
//
// Returns a ref that eases toward the source's value whenever it changes, so
// headline figures (TEV, asset value, liability) count up instead of snapping.
// Falls back to instant updates when the user prefers reduced motion.
import { ref, watch, onUnmounted } from 'vue'

export function useCountUp(source, duration = 700) {
  const out = ref(source.value)
  const reduced =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  let raf = 0

  watch(source, (to) => {
    cancelAnimationFrame(raf)
    if (to == null) {
      out.value = null
      return
    }
    if (reduced) {
      out.value = to
      return
    }
    const from = typeof out.value === 'number' ? out.value : 0
    const t0 = performance.now()
    const ease = (t) => 1 - Math.pow(1 - t, 3)
    const step = (now) => {
      const p = Math.min((now - t0) / duration, 1)
      out.value = from + (to - from) * ease(p)
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
  })

  onUnmounted(() => cancelAnimationFrame(raf))
  return out
}
