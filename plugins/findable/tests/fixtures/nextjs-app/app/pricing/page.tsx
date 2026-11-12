'use client';
import { useEffect, useState } from "react";

export default function Pricing() {
  const [plans, setPlans] = useState([]);
  useEffect(() => { fetch("/api/plans").then(r => r.json()).then(setPlans); }, []);
  return <main><h1>Pricing</h1>{plans.length}</main>;
}
