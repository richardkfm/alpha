<script setup>
// First-run orientation card: what to click, what the three headline numbers
// mean, and where Compare / Data Hub / display styles live. Shown once (App
// remembers the dismissal) and re-openable from the topbar's "?" button.
// Esc and a click on the backdrop close it; App owns the global Esc listener.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const emit = defineEmits(['close', 'go'])
const { t } = useI18n()
const primary = ref(null)

const STEPS = computed(() => [
  { icon: '◍', title: t('guide.steps.click.title'), body: t('guide.steps.click.body') },
  { icon: '$', title: t('guide.steps.numbers.title'), body: t('guide.steps.numbers.body') },
  { icon: '⌖', title: t('guide.steps.search.title'), body: t('guide.steps.search.body') },
  { icon: '▦', title: t('guide.steps.styles.title'), body: t('guide.steps.styles.body') },
])

// Move focus into the dialog so keyboard users land on its main action.
onMounted(() => primary.value?.focus())
</script>

<template>
  <div class="guide-scrim" @click.self="emit('close')">
    <section
      class="guide"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guide-title"
      aria-describedby="guide-lead"
    >
      <button class="guide-x" :aria-label="t('guide.close')" @click="emit('close')">×</button>
      <span class="guide-eyebrow">{{ t('guide.eyebrow') }}</span>
      <h2 id="guide-title">{{ t('guide.title') }}</h2>
      <p id="guide-lead" class="guide-lead">{{ t('guide.lead') }}</p>

      <ol class="steps">
        <li v-for="(s, i) in STEPS" :key="i" class="step">
          <span class="step-icon" aria-hidden="true">{{ s.icon }}</span>
          <span class="step-text">
            <span class="step-title">{{ s.title }}</span>
            <span class="step-body">{{ s.body }}</span>
          </span>
        </li>
      </ol>

      <p class="guide-note">{{ t('guide.note') }}</p>

      <footer class="guide-foot">
        <div class="guide-links">
          <button class="ghost" @click="emit('go', 'compare')">
            <span aria-hidden="true">⊞</span> {{ t('guide.openCompare') }}
          </button>
          <button class="ghost" @click="emit('go', 'data')">
            <span aria-hidden="true">⛁</span> {{ t('guide.openData') }}
          </button>
        </div>
        <button
          ref="primary"
          class="primary"
          data-test="onboarding-dismiss"
          @click="emit('close')"
        >{{ t('guide.start') }}</button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.guide-scrim {
  position: absolute;
  inset: 0;
  z-index: 1400; /* above the topbar: the guide is the only thing to act on */
  display: grid;
  place-items: center;
  padding: var(--space-4);
  /* A plain dim, no backdrop blur: blurring a live, spinning WebGL globe
     every frame is expensive on low-end GPUs. */
  background: var(--scrim);
}
.guide {
  position: relative;
  width: min(560px, 100%);
  max-height: calc(100% - 2 * var(--space-4));
  overflow-y: auto;
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, var(--bg-panel), var(--bg-deep));
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft), var(--shadow-glow);
  animation: guide-rise 0.4s var(--ease) both;
}
@keyframes guide-rise {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
}
.guide-x {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease);
}
.guide-x:hover {
  color: var(--accent);
  border-color: var(--accent);
}
.guide-eyebrow {
  font-size: var(--fs-2xs);
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--accent);
}
.guide h2 {
  margin: var(--space-1) 0 0;
  padding-right: 40px;
  font-size: var(--fs-xl);
  font-weight: 800;
  letter-spacing: -0.2px;
  color: var(--text);
}
.guide-lead {
  margin: var(--space-2) 0 var(--space-5);
  font-size: var(--fs-md);
  line-height: 1.5;
  color: var(--text-muted);
}

.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.step {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}
.step-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  font-weight: 800;
  color: var(--accent);
  background: var(--accent-bg);
  border: 1px solid var(--accent-border);
}
.step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.step-title {
  font-size: var(--fs-md);
  font-weight: 700;
  color: var(--text);
}
.step-body {
  font-size: var(--fs-sm);
  line-height: 1.5;
  color: var(--text-muted);
}

.guide-note {
  margin: var(--space-5) 0 0;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  background: var(--gold-bg);
  border: 1px solid var(--gold-border);
  font-size: var(--fs-xs);
  line-height: 1.5;
  color: var(--text-muted);
}

.guide-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-5);
}
.guide-links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.ghost {
  padding: 7px 14px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-soft);
  background: var(--bg-deep);
  color: var(--text-muted);
  font: inherit;
  font-size: var(--fs-xs);
  font-weight: 700;
  cursor: pointer;
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease);
}
.ghost:hover {
  color: var(--accent);
  border-color: var(--accent);
}
.primary {
  margin-left: auto;
  padding: 9px 22px;
  border-radius: var(--radius-pill);
  border: none;
  background: linear-gradient(180deg, var(--accent), var(--teal-strong));
  color: var(--on-accent);
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 2px 12px var(--accent-bg);
  transition: transform 0.15s var(--ease);
}
.primary:hover {
  transform: translateY(-1px);
}

@media (max-width: 560px) {
  .guide {
    padding: var(--space-5) var(--space-4);
  }
  .guide h2 {
    font-size: 1.25rem;
  }
  .guide-lead {
    font-size: var(--fs-sm);
    margin-bottom: var(--space-4);
  }
  .step-body {
    font-size: var(--fs-xs);
  }
  .guide-foot {
    flex-direction: column-reverse;
    align-items: stretch;
  }
  .primary {
    margin-left: 0;
  }
  .guide-links {
    justify-content: center;
  }
}
</style>
