import OpenAI from "openai";
const client = new OpenAI();
export async function write(prompt: string) {
  return client.responses.create({ model: "gpt-5", input: prompt });
}
export default function Blog() { return <p>Write blog posts in seconds.</p>; }
