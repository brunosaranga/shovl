import ground from "../../../assets/images/ground.webp";
import styles from "./Ground.module.css";

// The low-poly ground along the bottom of every page.
export default function Ground() {
    return <div className={styles.ground} style={{ backgroundImage: `url(${ground})` }} aria-hidden="true" />;
}
