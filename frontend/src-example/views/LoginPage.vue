<template>
  <div id="all-container">
    <div id="propaganda-container">
      <div id="hero-overlay">
        <h1 id="slogan">AI Empowered ·</h1>
        <SloganCarousel class="slogan-carousel" />
      </div>
    </div>
    <div id="login-container">
      <WelcomeAside />
    </div>
  </div>
</template>

<script setup>
import SloganCarousel from "@/components/LoginPage/SloganCarousel.vue";
import WelcomeAside from "@/components/LoginPage/WelcomeAside.vue";
import { useAuth } from "@/assets/static/js/useAuth"
import { onMounted } from "vue";
import router from "@/router/index.js";

const { isAuthenticated, user } = useAuth();

onMounted(() => {
  if (isAuthenticated.value === true) {
    if (user.value?.role === 'teacher') {
      router.replace('/teaching/portal')
    } else {
      router.replace('/portal')
    }
  }
})
</script>

<style scoped>
#all-container {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(420px, 1fr);
  min-height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--el-bg-color);
}

#propaganda-container {
  min-height: 100vh;
  background-image: linear-gradient(90deg, rgba(15, 16, 32, 0.72), rgba(35, 38, 88, 0.42)), url('@/assets/static/img/background.png');
  background-size: cover;
  background-position: center;
  position: relative;
}

#hero-overlay {
  position: relative;
  z-index: 2;
  padding: 48px 56px;
  min-height: 100vh;
}

#login-container {
  min-height: 100vh;
  width: 100%;
  box-shadow: inset 0 0 16px #8080FF;
  background: var(--el-bg-color);
}

#slogan {
  margin: 0 0 110px;
  font-size: 32px;
  font-weight: bold;
  color: #8080FF;
}

.slogan-carousel {
  max-width: 760px;
}

@media (max-width: 960px) {
  #all-container {
    grid-template-columns: 1fr;
  }

  #propaganda-container {
    min-height: 42vh;
  }

  #hero-overlay {
    min-height: 42vh;
    padding: 32px;
  }

  #login-container {
    min-height: 58vh;
  }
}
</style>
