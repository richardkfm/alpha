// alpha — entry point for the embeddable widget (/embed.html).
//
// A deliberately tiny, separate Vite entry so the iframe doesn't pull the heavy
// globe/map bundle that the main app (main.js) loads. Reads ?theme=light|dark to
// match the host page, then mounts the single EmbedCard component.
import { createApp } from 'vue'
import EmbedCard from './components/EmbedCard.vue'
import './theme.css'

const theme = new URLSearchParams(window.location.search).get('theme')
document.documentElement.classList.toggle('light', theme === 'light')

createApp(EmbedCard).mount('#embed')
