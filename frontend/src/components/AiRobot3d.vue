<template>
  <div class="ai-robot-3d">
    <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- Shadow -->
      <ellipse cx="40" cy="72" rx="24" ry="4" fill="black" opacity="0.06"/>
      <!-- Body glow -->
      <circle cx="40" cy="38" r="32" fill="#2563eb" opacity="0.06"/>
      <!-- Head -->
      <rect x="24" y="14" width="32" height="26" rx="8" fill="#2563eb" opacity="0.12"/>
      <!-- Antenna -->
      <line x1="40" y1="14" x2="40" y2="6" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" opacity="0.8"/>
      <circle cx="40" cy="5" r="3.5" fill="#2563eb" opacity="0.9"/>
      <!-- Eyes -->
      <circle cx="33" cy="26" r="4" fill="#2563eb"/>
      <circle cx="47" cy="26" r="4" fill="#2563eb"/>
      <circle cx="33" cy="26" r="1.5" fill="white"/>
      <circle cx="47" cy="26" r="1.5" fill="white"/>
      <!-- Mouth (smile) -->
      <path d="M33 35 C35 39, 45 39, 47 35" stroke="#2563eb" stroke-width="2" stroke-linecap="round" fill="none"/>
      <!-- Body -->
      <rect x="26" y="40" width="28" height="22" rx="6" fill="white" stroke="#2563eb" stroke-width="1.5"/>
      <!-- Chest screen -->
      <rect x="32" y="44" width="16" height="10" rx="3" fill="#2563eb" opacity="0.08"/>
      <text x="40" y="52" text-anchor="middle" font-size="8" fill="#2563eb" font-weight="600">AI</text>
      <!-- Arms -->
      <rect x="16" y="42" width="8" height="18" rx="4" fill="white" stroke="#2563eb" stroke-width="1.5"/>
      <rect x="56" y="42" width="8" height="18" rx="4" fill="white" stroke="#2563eb" stroke-width="1.5"/>
      <!-- Dots -->
      <circle cx="40" cy="44" r="2" fill="#2563eb" opacity="0.3"/>
    </svg>
  </div>
</template>

<style scoped>
.ai-robot-3d {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 299;
  cursor: pointer;
  transition: transform 0.3s ease;
  animation: float 6s ease-in-out infinite;
}

.ai-robot-3d:hover {
  transform: scale(1.1);
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-8px); }
}

@media (prefers-reduced-motion: reduce) {
  .ai-robot-3d {
    animation: none;
  }
}
</style>
