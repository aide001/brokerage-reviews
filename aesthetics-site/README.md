# Lumière Clinic website

Lumière Clinic is the clinic of Dr Lynn Morris, GP. Lumière is French for "light". Check the name is
free at Companies House and as a domain before using it.

A one-page website for a doctor-led aesthetics clinic. The content follows the
South Hampshire market and feasibility plan:

- **Main clinic in Chandler's Ford / Eastleigh.** The plan's recommended first base.
  New Forest and Poole/Sandbanks are listed as "register interest" clinic days, so
  the booking form shows where demand comes from before you commit to more rooms.
- **Positioning:** one GP owns the whole patient journey (assess, treat, review),
  honest suitability advice, natural results, follow-up included. No discount-led offers.
- **Prices** sit between the Southampton and Winchester price lists in the plan
  (around a £220 average spend). They are placeholders: set your own.
- **Advertising compliance:** botulinum toxin is a prescription-only medicine and
  cannot be advertised to the public (ASA/CAP). The page never names it or prices it,
  and "Lines & wrinkles" points to a consultation only. Under-18s are excluded and there
  are no time-limited deals (GMC cosmetic guidance).

## Before going live

1. Replace every `[placeholder]`: GMC number, qualifications, clinic
   address and postcode, phone, email, opening days.
2. `doctor.jpg` is cropped from a selfie and is a little blurry.
   A sharp professional headshot would look better.
3. Switch on online booking and deposits (see "Online booking" below).
4. Add a privacy notice and complaints procedure page (linked in the footer).
5. Have the final wording checked against current ASA/CAP and GMC guidance and your insurer's
   approved treatment list.

## Run locally

Open `index.html` in a browser, or run `python3 -m http.server` in this folder.

This folder is not part of the Brokerage Reviews deploy (`scripts/make_dist.py`
only copies the broker site's folders).

## Online booking

The "Book online" section shows a calendar of open days, start times for the chosen
treatment, and takes a 10% deposit. Settings are at the top of the `<script>` in
`index.html`: treatments and fees (`SERVICES`), opening hours (`HOURS`), minimum notice,
how many weeks ahead, closed dates and times already booked (`BOOKED`).

**Taking deposits (Stripe Payment Links, no server needed):**

1. Create a Stripe account at stripe.com and verify the business.
2. For each treatment, create a Payment Link for its deposit (Products → Payment Links),
   e.g. "Lip enhancement deposit" £21.00. Turn on "Collect customer phone number".
3. Paste each link into that treatment's `stripeLink` in `SERVICES`.

Visitors are sent to Stripe's secure page with their email filled in, and the booking
(treatment, date, time) appears on the payment as the reference, e.g. `lips_20261007_1000`.
Until a link is added, the button tells visitors to call or email instead.

**Limits of this static version:** the page can't see bookings made elsewhere, so a
paid slot stays visible to other visitors until you add it to `BOOKED`, and two people
could pay for the same time. Before going busy, move to a booking system that holds the
diary and takes deposits together (Fresha, Cliniko, Pabau or Calendly with Stripe), or
add a small server (for example a Cloudflare Worker) that stores bookings and creates
Stripe Checkout sessions.
