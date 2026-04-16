import type { ECharts } from 'echarts/core';
import * as echarts from 'echarts/core';
import type { Ref } from 'vue';
import { nextTick, onBeforeUnmount, watch } from 'vue';
// import type { VueECharts } from 'vue-echarts';

export function useEChart(
  chartRef: Ref<any | null>,
  option: Ref<any>,
  theme: Ref<string>,
  renderer: 'canvas' | 'svg' = 'canvas'
) {
  let chartInstance: ECharts | null = null;

  const initChart = async () => {
    if (!chartRef.value) return;

    await nextTick(); // DOM 업데이트 대기

    const dom = chartRef.value.getDom?.(); // VueECharts 인스턴스의 DOM
    if (!dom) return;

    if (chartInstance) {
      chartInstance.dispose();
    }

    chartInstance = echarts.init(dom, theme.value, { renderer });
    chartInstance.setOption(option.value);
  };

  // 테마가 바뀌면 전체 재생성
  watch(theme, () => {
    initChart();
  });

  // 옵션만 바뀌면 setOption만 적용
  watch(
    option,
    () => {
      if (chartInstance) {
        chartInstance.setOption(option.value, {
          notMerge: false,
          replaceMerge: ['series'],
        });
      }
    },
    { deep: true }
  );

  onBeforeUnmount(() => {
    chartInstance?.dispose();
    chartInstance = null;
  });

  return {
    initChart,
    getInstance: () => chartInstance,
  };
}
