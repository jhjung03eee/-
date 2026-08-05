import { useEffect, useState } from "react";

// Starts a bar at 0% and grows it to the real value on the next animation
// frame, so results feel like they're "filling in" rather than popping in
// fully formed.
export default function useFillWidth(target) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setWidth(target));
    return () => cancelAnimationFrame(id);
  }, [target]);
  return width;
}
