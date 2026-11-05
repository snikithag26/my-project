# Ethics, privacy and limits (for the report)

- **Not a diagnosis.** Screening, stress and expression outputs are support aids. The UI and PDF say so.
- **Consent.** Face enrolment needs a ticked consent box (parent/guardian for children). "Remove face data" deletes templates.
- **What is stored.** Face recognition keeps only a 128-number template per sample, never photos or video. Camera frames are processed in the browser and are not uploaded.
- **Access control.** Parents see only their own people. Teachers can view all but not edit. Therapists can view and edit all. Only the owner can delete.
- **Expression bias.** The expression model was trained mostly on neurotypical faces and can misread autistic expressions. Treat it as a prompt to check in.
- **Synthetic data.** The default ASD dataset and the stress dataset are simulated so the project runs end to end. Replace the ASD data with the UCI CSV for real results (see README) and keep the stress dataset labelled synthetic.
- **Production hardening not done:** HTTPS, rate limiting, encrypted database, audit log, password reset, face templates encrypted at rest.
