# South Hampshire Aesthetics website

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

1. Replace every `[placeholder]`: doctor's name, GMC number, qualifications, clinic
   address and postcode, phone, email, opening days.
2. `doctor.jpg` is cropped from a selfie, leaving out the NHS lanyard (NHS branding must not
   appear in private-practice marketing). A professional headshot would look better.
3. Connect the booking form. It currently checks the fields and shows the request for
   the visitor to email or phone in. Point it at a booking system (for example Fresha,
   Pabau or Cliniko) or a form service (for example Formspree).
4. Add a privacy notice and complaints procedure page (linked in the footer).
5. Have the final wording checked against current ASA/CAP and GMC guidance and your insurer's
   approved treatment list.

## Run locally

Open `index.html` in a browser, or run `python3 -m http.server` in this folder.

This folder is not part of the Brokerage Reviews deploy (`scripts/make_dist.py`
only copies the broker site's folders).
