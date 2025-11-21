import styles from "./SectionCard.module.css";

interface SectionCardProps {
  title: string;
  action?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

export function SectionCard({ title, action, children, className }: SectionCardProps) {
  return (
    <section className={`${styles.card} ${className ?? ""}`}>
      <div className={styles.header}>
        <p className={styles.title}>{title}</p>
        {action}
      </div>
      {children}
    </section>
  );
}
