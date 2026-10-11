export const fmtNumber = (n, digits = 2) => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "–";
  return Number(n).toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
};

export const fmtPct = (n, digits = 1) => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "–";
  return `${Number(n).toFixed(digits)}%`;
};

export const statusTone = (status) => {
  const key = (status || "").toUpperCase();
  if (key === "OK") return "ok";
  if (key === "WARNING") return "warning";
  if (key === "DRIFT") return "drift";
  if (key === "low") return "ok";
  if (key === "medium") return "warning";
  if (key === "high") return "drift";
  return "ok";
};
