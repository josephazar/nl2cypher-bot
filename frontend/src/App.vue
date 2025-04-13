<template>
  <div id="app">
    <header class="app-header">
      <div class="container">
        <div class="header-content">
          <div class="header-logo">🏙️</div>
          <div class="header-text">
            <h1 class="header-title">Badevel Living Lab Assistant</h1>
            <p class="header-subtitle">Explorez les données du village intelligent de Badevel</p>
          </div>
        </div>
      </div>
    </header>
    
    <main class="container my-4">
      <router-view/>
    </main>
    
    <footer class="container-fluid py-3 text-center">
      <p class="text-muted">© 2025 Badevel Living Lab</p>
    </footer>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
:root {
  --primary-color: #8c6ef2;
  --secondary-color: #e0d539;
  --light-primary: rgba(140, 110, 242, 0.1);
  --background-color: #f9fafd;
  --text-color: #333;
  --chat-user-bg: #f0f2f6;
  --chat-assistant-bg: rgba(140, 110, 242, 0.1);
  --border-radius: 12px;
  --box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

body {
  background-color: var(--background-color);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: var(--text-color);
  overflow-x: hidden;
}

/* Header styles */
.app-header {
  background: linear-gradient(90deg, var(--primary-color), var(--primary-color) 70%, var(--secondary-color));
  padding: 1.5rem 0;
  color: white;
  box-shadow: var(--box-shadow);
  margin-bottom: 2rem;
}

.header-content {
  display: flex;
  align-items: center;
}

.header-logo {
  font-size: 2.5rem;
  margin-right: 1rem;
}

.header-text {
  display: flex;
  flex-direction: column;
}

.header-title {
  font-size: 1.8rem;
  font-weight: 600;
  margin: 0;
}

.header-subtitle {
  font-size: 1rem;
  opacity: 0.9;
  margin: 0;
}

/* Import Bootstrap CSS via CDN */
@import url('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
</style>