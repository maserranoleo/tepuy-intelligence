"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type AnchorKind = "capital" | "oil" | "export" | "refinery";

type Anchor = {
  name: string;
  coords: [number, number];
  kind: AnchorKind;
};

const KEY_POINTS: Anchor[] = [
  { name: "Caracas", coords: [-66.9036, 10.4806], kind: "capital" },
  { name: "Maracaibo", coords: [-71.6125, 10.6427], kind: "oil" },
  { name: "Puerto La Cruz", coords: [-64.6932, 10.2127], kind: "export" },
  { name: "José Terminal", coords: [-64.8333, 10.1], kind: "export" },
  { name: "Orinoco Belt", coords: [-64.0, 8.5], kind: "oil" },
  { name: "Amuay Refinery", coords: [-70.2056, 11.7517], kind: "refinery" },
];

const INITIAL_CENTER: [number, number] = [-66.5, 7.5];
const INITIAL_ZOOM = 5.2;

function buildMarkerEl(anchor: Anchor): HTMLDivElement {
  const wrap = document.createElement("div");
  wrap.className = `tepuy-marker tepuy-marker--${anchor.kind}`;

  const dot = document.createElement("div");
  dot.className = "tepuy-marker-dot";

  const label = document.createElement("div");
  label.className = "tepuy-marker-label";
  label.textContent = anchor.name;

  wrap.appendChild(dot);
  wrap.appendChild(label);
  return wrap;
}

function fmt(n: number, d = 3) {
  return n.toFixed(d);
}

export default function VenezuelaMap({ maptilerKey }: { maptilerKey: string }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const [lat, setLat] = useState(INITIAL_CENTER[1]);
  const [lon, setLon] = useState(INITIAL_CENTER[0]);
  const [zoom, setZoom] = useState(INITIAL_ZOOM);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const style: string | StyleSpecification = maptilerKey
      ? `https://api.maptiler.com/maps/dataviz-dark/style.json?key=${maptilerKey}`
      : "https://tiles.openfreemap.org/styles/dark";

    const map = new maplibregl.Map({
      container: containerRef.current,
      style,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      minZoom: 4,
      maxZoom: 12,
      maxBounds: [
        [-90, -8],
        [-40, 25],
      ],
      attributionControl: { compact: true },
    });

    map.addControl(
      new maplibregl.NavigationControl({
        showCompass: false,
        showZoom: true,
        visualizePitch: false,
      }),
      "top-right"
    );

    map.on("load", () => {
      KEY_POINTS.forEach((anchor) => {
        new maplibregl.Marker({
          element: buildMarkerEl(anchor),
          anchor: "left",
        })
          .setLngLat(anchor.coords)
          .addTo(map);
      });
    });

    map.on("mousemove", (e) => {
      setLat(e.lngLat.lat);
      setLon(e.lngLat.lng);
    });

    map.on("zoom", () => {
      setZoom(map.getZoom());
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [maptilerKey]);

  return (
    <>
      <div ref={containerRef} className="map-container" />
      <div className="coords-readout">
        <span>{fmt(lat)}</span>°N · <span>{fmt(lon)}</span>°E ·{" "}
        z<span>{fmt(zoom, 1)}</span>
      </div>
    </>
  );
}
