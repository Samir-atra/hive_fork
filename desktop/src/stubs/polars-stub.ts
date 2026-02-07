/**
 * A browser-safe stub for nodejs-polars to allow the UI to run in a browser.
 */
export const DataFrame = (data: any) => {
  return {
    groupBy: (col: string) => ({
      agg: (op: any) => ({
        toString: () => {
          const keys = Object.keys(data);
          const firstKey = keys[0];
          const len = (data[firstKey] as any[]).length;
          return `Browser Mock DataFrame: ${len} rows grouped by ${col}`;
        }
      })
    })
  };
};

export const count = (col: string) => {
  return { op: 'count', column: col };
};

export default {
  DataFrame,
  count
};
