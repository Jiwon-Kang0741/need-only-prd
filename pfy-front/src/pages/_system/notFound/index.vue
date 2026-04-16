<template>
  <div class="not-found">
    <h1>404</h1>
    <p>페이지를 찾을 수 없습니다.</p>
    <a href="/">홈으로</a>
  </div>
</template>

<script lang="ts" setup>
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: 16px;
}
</style>
