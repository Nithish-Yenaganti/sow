import Stripe from "stripe";
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function checkout() {
  return stripe.checkout.sessions.create({ mode: "subscription", line_items: [{ price: "price_123", quantity: 1 }] });
}

export default function Pricing() {
  return <p>Pro plan: $20 per month.</p>;
}
