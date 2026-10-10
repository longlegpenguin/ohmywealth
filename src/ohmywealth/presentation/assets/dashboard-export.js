(function () {
    "use strict";

    const WIDTH = 1440;
    const PADDING = 64;
    const CONTENT_WIDTH = WIDTH - PADDING * 2;
    const GREEN = "#087f70";
    const INK = "#16302b";
    const MUTED = "#627873";
    const BORDER = "#dce8e4";
    const PALE = "#edf7f4";

    function selectedText(id) {
        const root = document.getElementById(id);
        if (!root) return "—";
        const value = root.querySelector(
            ".Select-value-label, [class*='singleValue']"
        );
        return (value ? value.textContent : root.textContent).trim() || "—";
    }

    function chartHeight(id, fallback) {
        const root = document.getElementById(id);
        const graph = root && (root.querySelector(".js-plotly-plot") || root);
        const height = graph && graph._fullLayout && graph._fullLayout.height;
        return Math.max(360, Math.min(Number(height) || fallback, 760));
    }

    function loadImage(source) {
        return new Promise(function (resolve, reject) {
            const image = new Image();
            image.onload = function () { resolve(image); };
            image.onerror = reject;
            image.src = source;
        });
    }

    async function plotImage(id, width, height) {
        const root = document.getElementById(id);
        const graph = root && (root.querySelector(".js-plotly-plot") || root);
        if (!graph || !window.Plotly) return null;
        const source = await window.Plotly.toImage(graph, {
            format: "png",
            width: width,
            height: height,
            scale: 1
        });
        return loadImage(source);
    }

    function roundedRect(ctx, x, y, width, height, radius, fill, stroke) {
        ctx.beginPath();
        ctx.roundRect(x, y, width, height, radius);
        if (fill) {
            ctx.fillStyle = fill;
            ctx.fill();
        }
        if (stroke) {
            ctx.strokeStyle = stroke;
            ctx.lineWidth = 1;
            ctx.stroke();
        }
    }

    function fitText(ctx, value, width) {
        const text = String(value || "");
        if (ctx.measureText(text).width <= width) return text;
        let shortened = text;
        while (shortened.length && ctx.measureText(shortened + "…").width > width) {
            shortened = shortened.slice(0, -1);
        }
        return shortened + "…";
    }

    function drawChart(ctx, image, y, width, height, x) {
        roundedRect(ctx, x, y, width, height, 14, "#ffffff", BORDER);
        if (image) ctx.drawImage(image, x + 1, y + 1, width - 2, height - 2);
    }

    function tableRows() {
        const cells = document.querySelectorAll(
            "#holdings-table [data-dash-row][data-dash-column]"
        );
        const rows = new Map();
        cells.forEach(function (cell) {
            const row = Number(cell.getAttribute("data-dash-row"));
            const column = cell.getAttribute("data-dash-column");
            if (!rows.has(row)) rows.set(row, {});
            const record = rows.get(row);
            if (!record[column]) record[column] = cell.textContent.trim();
        });
        return Array.from(rows.entries())
            .sort(function (left, right) { return left[0] - right[0]; })
            .map(function (entry) { return entry[1]; });
    }

    function drawTable(ctx, y, rows) {
        const columns = [
            ["name", "Holding", 250],
            ["kind", "Class", 130],
            ["quantity", "Units / balance", 165],
            ["price", "Price", 160],
            ["fx", "FX", 100],
            ["value", "Value", 180],
            ["month", "Month", 105],
            ["time", "Quote time", 222]
        ];
        const rowHeight = 38;
        const height = rowHeight * (rows.length + 1);
        roundedRect(ctx, PADDING, y, CONTENT_WIDTH, height, 12, "#ffffff", BORDER);
        ctx.textBaseline = "middle";
        let x = PADDING;
        columns.forEach(function (column) {
            ctx.fillStyle = PALE;
            ctx.fillRect(x, y, column[2], rowHeight);
            ctx.fillStyle = INK;
            ctx.font = "600 14px Inter, Arial, sans-serif";
            ctx.fillText(column[1], x + 10, y + rowHeight / 2);
            x += column[2];
        });
        rows.forEach(function (row, rowIndex) {
            let cellX = PADDING;
            const cellY = y + rowHeight * (rowIndex + 1);
            ctx.strokeStyle = "#e5eeeb";
            ctx.beginPath();
            ctx.moveTo(PADDING, cellY);
            ctx.lineTo(PADDING + CONTENT_WIDTH, cellY);
            ctx.stroke();
            columns.forEach(function (column) {
                ctx.fillStyle = INK;
                ctx.font = "13px Inter, Arial, sans-serif";
                ctx.fillText(
                    fitText(ctx, row[column[0]], column[2] - 20),
                    cellX + 10,
                    cellY + rowHeight / 2
                );
                cellX += column[2];
            });
        });
        return height;
    }

    async function exportDashboard() {
        const button = document.getElementById("export-dashboard-png");
        const status = document.getElementById("export-png-status");
        if (!button || button.disabled) return;
        button.disabled = true;
        if (status) status.textContent = "Rendering…";

        try {
            const fullCharts = [
                ["wealth-history", chartHeight("wealth-history", 420)],
                ["class-history", chartHeight("class-history", 480)],
                ["overall-account-changes", chartHeight("overall-account-changes", 600)],
                ["account-changes", chartHeight("account-changes", 560)]
            ];
            const compositionHeight = Math.max(
                chartHeight("class-composition", 460),
                chartHeight("asset-composition", 560)
            );
            const halfWidth = (CONTENT_WIDTH - 20) / 2;
            const chartImages = await Promise.all(
                fullCharts.map(function (chart) {
                    return plotImage(chart[0], CONTENT_WIDTH, chart[1]);
                })
            );
            const compositionImages = await Promise.all([
                plotImage("class-composition", halfWidth, compositionHeight),
                plotImage("asset-composition", halfWidth, compositionHeight)
            ]);
            const rows = tableRows();
            const tableHeight = 38 * (rows.length + 1);
            const fullChartHeight = fullCharts.reduce(function (sum, chart) {
                return sum + chart[1] + 20;
            }, 0);
            const height = 420 + fullChartHeight + compositionHeight + tableHeight;
            const canvas = document.createElement("canvas");
            canvas.width = WIDTH;
            canvas.height = height;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#f5f8f7";
            ctx.fillRect(0, 0, WIDTH, height);

            let y = 58;
            ctx.fillStyle = INK;
            ctx.font = "700 32px Inter, Arial, sans-serif";
            ctx.fillText("Oh My Wealth", PADDING, y);
            ctx.fillStyle = MUTED;
            ctx.font = "15px Inter, Arial, sans-serif";
            ctx.textAlign = "right";
            ctx.fillText(
                "Generated " + new Date().toLocaleString(),
                WIDTH - PADDING,
                y
            );
            ctx.textAlign = "left";

            y += 38;
            roundedRect(ctx, PADDING, y, CONTENT_WIDTH, 76, 12, "#ffffff", BORDER);
            ctx.fillStyle = MUTED;
            ctx.font = "14px Inter, Arial, sans-serif";
            ctx.fillText(
                "Reporting currency  " + selectedText("reporting-currency") +
                "     Assets  " +
                (document.getElementById("dashboard-filter-summary")?.textContent.trim() || "—"),
                PADDING + 20,
                y + 30
            );
            ctx.fillText(
                "Period  " + selectedText("history-start-month") + " " +
                selectedText("history-start-year") + "  →  " +
                selectedText("history-end-month") + " " + selectedText("history-end-year"),
                PADDING + 20,
                y + 55
            );

            y += 116;
            ctx.fillStyle = INK;
            ctx.font = "700 22px Inter, Arial, sans-serif";
            ctx.fillText("Period analysis", PADDING, y);
            y += 20;
            for (let index = 0; index < 3; index += 1) {
                drawChart(
                    ctx,
                    chartImages[index],
                    y,
                    CONTENT_WIDTH,
                    fullCharts[index][1],
                    PADDING
                );
                y += fullCharts[index][1] + 20;
            }

            y += 18;
            ctx.fillStyle = INK;
            ctx.font = "700 22px Inter, Arial, sans-serif";
            ctx.fillText("Monthly snapshot", PADDING, y);
            ctx.fillStyle = MUTED;
            ctx.font = "14px Inter, Arial, sans-serif";
            ctx.fillText(
                selectedText("snapshot-month") + " " + selectedText("snapshot-year"),
                PADDING + 205,
                y
            );
            y += 22;
            const metricWidth = (CONTENT_WIDTH - 20) / 2;
            roundedRect(ctx, PADDING, y, metricWidth, 82, 12, PALE, null);
            roundedRect(ctx, PADDING + metricWidth + 20, y, metricWidth, 82, 12, PALE, null);
            ctx.fillStyle = MUTED;
            ctx.font = "13px Inter, Arial, sans-serif";
            ctx.fillText("Selected month wealth", PADDING + 18, y + 25);
            ctx.fillText("Monthly change", PADDING + metricWidth + 38, y + 25);
            ctx.fillStyle = INK;
            ctx.font = "700 24px Inter, Arial, sans-serif";
            ctx.fillText(
                document.getElementById("wealth-total")?.textContent.trim() || "—",
                PADDING + 18,
                y + 58
            );
            ctx.fillText(
                document.getElementById("wealth-growth")?.textContent.trim() || "—",
                PADDING + metricWidth + 38,
                y + 58
            );
            y += 102;
            drawChart(ctx, chartImages[3], y, CONTENT_WIDTH, fullCharts[3][1], PADDING);
            y += fullCharts[3][1] + 20;
            drawChart(ctx, compositionImages[0], y, halfWidth, compositionHeight, PADDING);
            drawChart(
                ctx,
                compositionImages[1],
                y,
                halfWidth,
                compositionHeight,
                PADDING + halfWidth + 20
            );
            y += compositionHeight + 20;
            drawTable(ctx, y, rows);

            await new Promise(function (resolve, reject) {
                canvas.toBlob(function (blob) {
                    if (!blob) {
                        reject(new Error("The browser could not create the PNG"));
                        return;
                    }
                    const link = document.createElement("a");
                    link.download = "oh-my-wealth-" + new Date().toISOString().slice(0, 10) + ".png";
                    link.href = URL.createObjectURL(blob);
                    link.click();
                    setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
                    resolve();
                }, "image/png");
            });
            if (status) status.textContent = "Downloaded";
        } catch (error) {
            console.error("Dashboard PNG export failed", error);
            if (status) status.textContent = "Export failed";
            window.alert("Could not export the Dashboard PNG. Please try again after all charts finish loading.");
        } finally {
            button.disabled = false;
            setTimeout(function () {
                if (status) status.textContent = "";
            }, 3000);
        }
    }

    function attach() {
        const button = document.getElementById("export-dashboard-png");
        if (!button || button.dataset.pngExportReady) return;
        button.dataset.pngExportReady = "true";
        button.addEventListener("click", exportDashboard);
    }

    new MutationObserver(attach).observe(document.documentElement, {
        childList: true,
        subtree: true
    });
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", attach);
    } else {
        attach();
    }
})();
