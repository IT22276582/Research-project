"use client";

import styles from "./TabNavigation.module.css";

interface Tab {
  id: string;
  label: string;
}

interface TabNavigationProps {
  activeTab: string;
  tabs: Tab[];
  onTabChange: (tab: string) => void;
}

export function TabNavigation({ activeTab, tabs, onTabChange }: TabNavigationProps) {
  return (
    <div className={styles.wrapper}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onTabChange(tab.id)}
          className={`${styles.tab} ${activeTab === tab.id ? styles.active : ""}`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
