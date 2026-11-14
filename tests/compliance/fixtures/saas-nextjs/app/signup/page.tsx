export default function Signup() {
  return (
    <form>
      <input type="email" name="email" />
      <input type="password" name="password" />
      <input name="first_name" />
      <label><input type="checkbox" name="newsletter" defaultChecked /> Send me product updates and offers</label>
      <button>Create account</button>
    </form>
  );
}
