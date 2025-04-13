<template>
    <div class="loading-icon-container">
      <div class="loading-icon"></div>
    </div>
  </template>
  
  <script>
  export default {
    name: 'LoadingIcon'
  }
  </script>
  
  <style scoped>
  .loading-icon-container {
    display: flex;
    justify-content: center;
    padding: 20px 0;
  }
  
  .loading-icon {
    display: inline-block;
    position: relative;
    width: 64px;
    height: 20px;
  }
  
  .loading-icon:after {
    content: " ";
    display: block;
    position: absolute;
    width: 64px;
    height: 20px;
    border-radius: 5px;
    background-color: var(--light-primary);
    background-image: linear-gradient(90deg, var(--light-primary) 0%, var(--primary-color) 50%, var(--light-primary) 100%);
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
  }
  
  @keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
  </style>