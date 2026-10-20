import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

const STYLE_SELECTOR = 'style, link[rel="stylesheet"]'

// Popup has an empty document: copy the opener's styles + theme and keep them in sync
// (Vite HMR swaps <style> tags, the theme toggle flips data-theme on <html>)
function useMirroredStyles(win) {
  useEffect(() => {
    const doc = win.document
    let clones = []
    const sync = () => {
      clones.forEach((node) => node.remove())
      clones = [...document.querySelectorAll(STYLE_SELECTOR)].map((node) => doc.head.appendChild(node.cloneNode(true)))
      doc.documentElement.dataset.theme = document.documentElement.dataset.theme
    }
    sync()

    const observer = new MutationObserver(sync)
    observer.observe(document.head, { childList: true, subtree: true, characterData: true })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [win])
}

// Renders children into a window opened with window.open('') - a micro-session wired to the main window's state
export default function PopupWindow({ win, title, onClosed, onFocus, children }) {
  const [container, setContainer] = useState(null)
  useMirroredStyles(win)

  useEffect(() => {
    const doc = win.document
    doc.title = title
    doc.documentElement.lang = document.documentElement.lang
    const root = doc.createElement('div')
    doc.body.replaceChildren(root)
    setContainer(root)

    win.addEventListener('pagehide', onClosed)
    win.addEventListener('focus', onFocus)
    return () => {
      win.removeEventListener('pagehide', onClosed)
      win.removeEventListener('focus', onFocus)
      root.remove()
    }
  }, [win])

  useEffect(() => {
    win.document.title = title
  }, [win, title])

  if (!container) return null
  return createPortal(children, container)
}
