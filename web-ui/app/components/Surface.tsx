"use client";

import { ReactNode } from "react";
import styles from "./Surface.module.css";

type SurfaceProps = {
  children: ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  element?: keyof JSX.IntrinsicElements;
};

export function Surface({
  children,
  className = "",
  padding = "md",
  element: Element = "section",
}: SurfaceProps) {
  const paddingClass =
    padding === "none"
      ? styles.paddingNone
      : padding === "sm"
      ? styles.paddingSm
      : padding === "lg"
      ? styles.paddingLg
      : styles.paddingMd;

  const classes = [styles.surface, paddingClass, className].filter(Boolean).join(" ");

  return <Element className={classes}>{children}</Element>;
}
