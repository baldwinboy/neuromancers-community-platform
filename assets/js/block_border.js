/**
 * Block Border System
 *
 * Generates resizable decorative SVG borders (top/bottom) for content blocks.
 * Two categories:
 *   - Tiling borders (zigzag, wave, legoWave): small SVG tiles that repeat-x
 *   - Full-width borders (leftCurve, rightCurve, rounded): single SVG stretched to 100% width
 *
 * Each border type provides a polygon (filled shape) and a polyline (stroke outline).
 * The polygon is used as background-image on the container's ::before/::after pseudo-element.
 * The polyline is used when an explicit border color is set (overlaid via .block-border--color).
 */

function createStyledBorder(
  borderStyle,
  createPolygonSvgFn,
  createPolylineSvgFn,
) {
  const main = document.querySelector("main");
  if (!main) return;
  const containers = main.querySelectorAll(
    `[data-border-style="${borderStyle}"]`,
  );
  if (containers.length === 0) return;
  const windowWidth = window.innerWidth;
  const isGtDesktop = windowWidth >= 1280;
  const isGtTablet = windowWidth >= 768;
  containers.forEach((container) => {
    const color = getComputedStyle(container).color;
    if (!color) return;
    const isTop = container.classList.contains("block-border--top");
    const rotate = isTop ? "180 8 4" : "0 8 4";
    const size = isGtDesktop ? 80 : isGtTablet ? 40 : 20;
    const polygon = createPolygonSvgFn(color, size, rotate);
    const polygonDataUrl = `data:image/svg+xml;base64,${btoa(new XMLSerializer().serializeToString(polygon))}`;
    container.style.setProperty("--polygon", `url("${polygonDataUrl}")`);

    const polyline = createPolylineSvgFn(color, size, rotate);
    const polylineDataUrl = `data:image/svg+xml;base64,${btoa(new XMLSerializer().serializeToString(polyline))}`;
    container.style.setProperty("--polyline", `url("${polylineDataUrl}")`);

    const hasBorderColor = container.dataset.hasBorderColor === "true";
    if (hasBorderColor) {
      const borderColorContainer = container.querySelector(
        ".block-border--color",
      );
      if (borderColorContainer) {
        const borderColor = getComputedStyle(borderColorContainer).color;
        if (!borderColor) return;
        const borderPolyline = createPolylineSvgFn(borderColor, size, rotate);
        const borderPolylineDataUrl = `data:image/svg+xml;base64,${btoa(new XMLSerializer().serializeToString(borderPolyline))}`;
        borderColorContainer.style.setProperty(
          "--polyline",
          `url("${borderPolylineDataUrl}")`,
        );
      }
    }
  });
}

/**
 * Full-width borders use a single SVG that stretches across the container.
 * The SVG uses viewBox + preserveAspectRatio="none" so it scales to any width.
 * We set the container width directly and override background-size/repeat via CSS.
 */
function createFullWidthBorder(
  borderStyle,
  createPolygonSvgFn,
  createPolylineSvgFn,
) {
  const main = document.querySelector("main");
  if (!main) return;
  const containers = main.querySelectorAll(
    `[data-border-style="${borderStyle}"]`,
  );
  if (containers.length === 0) return;
  containers.forEach((container) => {
    const color = getComputedStyle(container).color;
    if (!color) return;
    const isTop = container.classList.contains("block-border--top");
    const containerWidth = container.parentElement
      ? container.parentElement.offsetWidth
      : window.innerWidth;

    const polygon = createPolygonSvgFn(color, containerWidth, isTop);
    const polygonDataUrl = `data:image/svg+xml;base64,${btoa(new XMLSerializer().serializeToString(polygon))}`;
    container.style.setProperty("--polygon", `url("${polygonDataUrl}")`);

    const polyline = createPolylineSvgFn(color, containerWidth, isTop);
    const polylineDataUrl = `data:image/svg+xml;base64,${btoa(new XMLSerializer().serializeToString(polyline))}`;
    container.style.setProperty("--polyline", `url("${polylineDataUrl}")`);

    const hasBorderColor = container.dataset.hasBorderColor === "true";
    if (hasBorderColor) {
      const borderColorContainer = container.querySelector(
        ".block-border--color",
      );
      if (borderColorContainer) {
        const borderColor = getComputedStyle(borderColorContainer).color;
        if (!borderColor) return;
        const borderPolyline = createPolylineSvgFn(
          borderColor,
          containerWidth,
          isTop,
        );
        const borderPolylineDataUrl = `data:image/svg+xml;base64,${btoa(new XMLSerializer().serializeToString(borderPolyline))}`;
        borderColorContainer.style.setProperty(
          "--polyline",
          `url("${borderPolylineDataUrl}")`,
        );
      }
    }
  });
}

function createZigzagPolygonSvg(color, size, rotate) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const scale = size / 16;
  svg.setAttribute("width", `${size}px`);
  svg.setAttribute("height", `${size / 2}px`);
  svg.setAttribute("fill", color);

  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const polygon = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "polygon",
  );

  const transform = [
    scale ? `scale(${scale})` : "",
    rotate ? `rotate(${rotate})` : "",
  ]
    .join(" ")
    .trim();

  polygon.setAttribute("points", "0,0 8,8 16,0");
  polygon.setAttribute("transform", transform);
  g.appendChild(polygon);
  svg.appendChild(g);
  return svg;
}

function createZigzagPolylineSvg(color, size, rotate) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const scale = size / 16;
  svg.setAttribute("width", `${size}px`);
  svg.setAttribute("height", `${size / 2}px`);
  svg.setAttribute("fill", "none");

  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const polyline = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "polyline",
  );

  const transform = [
    scale ? `scale(${scale})` : "",
    rotate ? `rotate(${rotate})` : "",
  ]
    .join(" ")
    .trim();

  polyline.setAttribute("points", "0,0 8,8 16,0");
  polyline.setAttribute("transform", transform);
  polyline.setAttribute("stroke", color);
  polyline.setAttribute("stroke-width", "2");
  polyline.setAttribute("vector-effect", "non-scaling-stroke");
  g.appendChild(polyline);
  svg.appendChild(g);
  return svg;
}

function createZigzagBorder() {
  createStyledBorder("zigzag", createZigzagPolygonSvg, createZigzagPolylineSvg);
}

function createWavePolygonSvg(color, width, isTop) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", `${width}px`);
  svg.setAttribute("height", "100px");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("fill", color);

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  if (isTop) {
    path.setAttribute("d", "M0,0 C30,220 70,-100 100,40 L100,100 L0,100 Z");
  } else {
    path.setAttribute("d", "M0,0 L100,0 L100,40 C70,220 30,-100 0,100 Z");
  }
  svg.appendChild(path);
  return svg;
}

function createWavePolylineSvg(color, width, isTop) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", `${width}px`);
  svg.setAttribute("height", "100px");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("fill", "none");

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  if (isTop) {
    path.setAttribute("d", "M0,0 C30,220 70,-100 100,40");
  } else {
    path.setAttribute("d", "M0,0 L100,0 L100,40 C70,220 30,-100 0,100 Z");
  }
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", "2");
  path.setAttribute("vector-effect", "non-scaling-stroke");
  svg.appendChild(path);
  return svg;
}

function createWaveBorder() {
  createFullWidthBorder("wave", createWavePolygonSvg, createWavePolylineSvg);
}

function createLegoWavePolygonSvg(color, size, rotate) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const scale = size / 16;
  svg.setAttribute("width", `${size}px`);
  svg.setAttribute("height", `${size / 2}px`);
  svg.setAttribute("fill", color);

  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");

  const transform = [
    scale ? `scale(${scale})` : "",
    rotate ? `rotate(${rotate})` : "",
  ]
    .join(" ")
    .trim();

  // Lego wave: block-shaped dome per tile — flat top with vertical sides
  path.setAttribute("d", "M0,0 L2.5,0 L2.5,6 L13.5,6 L13.5,0 L16,0 Z");
  path.setAttribute("transform", transform);
  g.appendChild(path);
  svg.appendChild(g);
  return svg;
}

function createLegoWavePolylineSvg(color, size, rotate) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const scale = size / 16;
  svg.setAttribute("width", `${size}px`);
  svg.setAttribute("height", `${size / 2}px`);
  svg.setAttribute("fill", "none");

  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");

  const transform = [
    scale ? `scale(${scale})` : "",
    rotate ? `rotate(${rotate})` : "",
  ]
    .join(" ")
    .trim();

  path.setAttribute("d", "M0,0 L2.5,0 L2.5,6 L13.5,6 L13.5,0 L16,0");
  path.setAttribute("transform", transform);
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", "2");
  path.setAttribute("vector-effect", "non-scaling-stroke");
  g.appendChild(path);
  svg.appendChild(g);
  return svg;
}

function createLegoWaveBorder() {
  createStyledBorder(
    "legoWave",
    createLegoWavePolygonSvg,
    createLegoWavePolylineSvg,
  );
}

function createLeftCurvePolygonSvg(color, width, isTop) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", `${width}px`);
  svg.setAttribute("height", `100px`);
  svg.setAttribute("viewBox", `0 0 100 100`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("fill", color);

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M100,100 C100,99 40,99 20,50 L-1,-1 L-1,100 Z");

  if (isTop) {
    path.setAttribute("d", "M100,100 C100,99 40,99 20,50 L-1,-1 L-1,100 Z");
  } else {
    path.setAttribute("d", "M100,100 C100,98 40,98 20,50 L-1,-1 L100,0");
  }

  path.setAttribute("vector-effect", "non-scaling-size");
  svg.appendChild(path);
  return svg;
}

function createLeftCurvePolylineSvg(color, width, isTop) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", `${width}px`);
  svg.setAttribute("height", `100px`);
  svg.setAttribute("viewBox", `0 0 100 100`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("fill", "none");

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");

  if (isTop) {
    path.setAttribute("d", `M100,100 C100,99 40,99 20,50 L-1,-1`);
  } else {
    path.setAttribute("d", `M100,100 C100,99 40,99 20,50 L-1,-1 L100,0`);
  }
  
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", "2");
  path.setAttribute("vector-effect", "non-scaling-stroke");
  svg.appendChild(path);
  return svg;
}

function createLeftCurveBorder() {
  createFullWidthBorder(
    "leftCurve",
    createLeftCurvePolygonSvg,
    createLeftCurvePolylineSvg,
  );
}

function createRightCurvePolygonSvg(color, width, isTop) {
  const height = Math.round(width * 0.08);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", `${width}px`);
  svg.setAttribute("height", `100px`);
  svg.setAttribute("viewBox", `0 0 100 100`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("fill", color);

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M100,100 C100,99 40,99 20,50 L-1,-1 L-1,100 Z");

  if (isTop) {
    path.setAttribute("d", "M100,100 C100,99 40,99 20,50 L-1,-1 L-1,100 Z");
  } else {
    path.setAttribute("d", "M100,100 C100,98 40,98 20,50 L-1,-1 L100,0");
  }

  // Flip horizontally by scaling X by -1 and translating back into view
  path.setAttribute("transform", `scale(-1,1) translate(-100,0)`);
  path.setAttribute("vector-effect", "non-scaling-size");
  svg.appendChild(path);
  return svg;
}

function createRightCurvePolylineSvg(color, width, isTop) {
const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", `${width}px`);
  svg.setAttribute("height", `100px`);
  svg.setAttribute("viewBox", `0 0 100 100`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("fill", "none");

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");

  if (isTop) {
    path.setAttribute("d", `M100,100 C100,99 40,99 20,50 L-1,-1`);
  } else {
    path.setAttribute("d", `M100,100 C100,99 40,99 20,50 L-1,-1 L100,0`);
  }
  
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", "2");
  // Flip horizontally by scaling X by -1 and translating back into view
  path.setAttribute("transform", `scale(-1,1) translate(-100,0)`);
  path.setAttribute("vector-effect", "non-scaling-stroke");
  svg.appendChild(path);
  return svg;
}

function createRightCurveBorder() {
  createFullWidthBorder(
    "rightCurve",
    createRightCurvePolygonSvg,
    createRightCurvePolylineSvg,
  );
}

function createRoundedPolygonSvg(color, width, isTop) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", `${width}px`);
  svg.setAttribute("height", "100px");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("fill", color);

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  if (isTop) {
    // Top: arc bows upward
    path.setAttribute("d", "M0,100 C50,0 50,0 100,100");
  } else {
    // Bottom: arc bows downward
    path.setAttribute("d", `M0,0 C50,100 50,100 100,0`);
  }
  svg.appendChild(path);
  return svg;
}

function createRoundedPolylineSvg(color, width, isTop) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", `${width}px`);
  svg.setAttribute("height", "100px");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("fill", "none");

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  if (isTop) {
    path.setAttribute("d", "M0,100 C50,0 50,0 100,100");
  } else {
    path.setAttribute("d", `M0,0 C50,100 50,100 100,0`);
  }
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", "2");
  path.setAttribute("vector-effect", "non-scaling-stroke");
  svg.appendChild(path);
  return svg;
}

function createRoundedBorder() {
  createFullWidthBorder(
    "rounded",
    createRoundedPolygonSvg,
    createRoundedPolylineSvg,
  );
}

function createBlockBorders() {
  createZigzagBorder();
  createWaveBorder();
  createLegoWaveBorder();
  createLeftCurveBorder();
  createRightCurveBorder();
  createRoundedBorder();
}

function debouncedCreateBlockBorders() {
  requestAnimationFrame(createBlockBorders);
}

window.addEventListener("load", createBlockBorders);
document.addEventListener("DOMContentLoaded", createBlockBorders);
window.addEventListener("resize", debouncedCreateBlockBorders);
