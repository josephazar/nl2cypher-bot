<template>
    <div class="timer">{{ displayTime }}</div>
  </template>
  
  <script>
  export default {
    name: 'MyTimer',
    data() {
      return {
        seconds: 0,
        timer: null
      }
    },
    computed: {
      displayTime() {
        const minutes = Math.floor(this.seconds / 60)
        const secs = this.seconds % 60
        return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
      }
    },
    methods: {
      start() {
        this.seconds = 0
        this.timer = setInterval(() => {
          this.seconds++
        }, 1000)
      },
      stop() {
        if (this.timer) {
          clearInterval(this.timer)
          this.timer = null
        }
      },
      reset() {
        this.seconds = 0
      }
    },
    beforeDestroy() {
      this.stop()
    }
  }
  </script>
  
  <style scoped>
  .timer {
    font-size: 1.2rem;
    font-weight: bold;
    color: var(--primary-color);
    display: inline-block;
    padding: 0 10px;
  }
  </style>