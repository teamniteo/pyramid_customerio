## Changelog

1.1.0 (2026-11-05)
-----------

* Add support for Customer.io Objects: `identify_object`, `delete_object` and
  `delete_object_relationships` on `request.customerio`, configured through
  the `customerio.object_types`, `customerio.object_properties` and
  `customerio.relationship_properties` settings.
  [zupo]

1.0.0
-----------

* Init `pyramid_customerio`, forked from `pyramid_mixpanel`.

---

## Historical Changelog (from pyramid_mixpanel)

0.13.0 (2024-03-08)
-------------------

* MixpanelQuery.profile_by_email raises a custom exception called
  `MultipleProfilesFoundException` when multiple profiles are found for a given email.
  The exception contains the email and all profiles found so that clients can handle
  the exception as needed.
  [karantan]


0.12.0 (2022-03-22)
-------------------

* Overhauled testing support for more readable asserts. This is a breaking
  change for existing test cases.
  [zupo]


0.11.0 (2022-02-10)
-------------------

* Support for skipping arbitrary track/profile_set calls to Customer.io.
  [zupo]


0.10.2 (2021-12-13)
------------------

* Customer.io expects the main "sign up" timestamp to be sent as `created_at`.
  [zupo]


0.10.1 (2021-12-13)
------------------

* Fix another brownbag release by re-applying fixes from 0.9.1.
  [zupo]


0.10.0 (2021-12-13)
------------------

* Support different date formatting between Mixpanel and Customer.io.
  [zupo]


0.9.1 (2021-09-24)
------------------

* Fix brownbag release by fixing definition of extras.
  [zupo]


0.9.0 (2021-09-24)
------------------

* Add optional support for Customer.io.
  [zupo]


0.8.0 (2020-05-11)
------------------

* Make structlog optional.
  [am-on]

* Support setting event props from HTTP headers.
  [am-on]


0.7.0 (2019-12-19)
------------------

* Added support for `people_union()`.
  [am-on]

* Added `sayanarijit/typecov`.
  [sayanarijit]


0.6.0 (2019-08-26)
------------------

* Added support for configuring a custom Consumer.
  [zupo]


0.5.0 (2019-08-25)
------------------

* Require that all Consumers implement a `flush()` method.
  [zupo]


0.4.3 (2019-08-24)
------------------

* Include py.typed in the package, third time is the charm?
  [zupo]


0.4.2 (2019-08-24)
------------------

* Include py.typed in the package, now for real.
  [zupo]


0.4.1 (2019-08-24)
------------------

* Include py.typed in the package.
  [zupo]


0.4.0 (2019-08-19)
------------------

* Prepare for PYPI release of the rewrite.
  [zupo]

* Small performance optimization.
  [zupo]


0.3.0 (2019-08-09)
------------------

* Add guards that make sure parameters sent to MixpanelTrack are valid.
  [zupo]

* Don't flood logs with "mixpanel configured" messages.
  [zupo]

* Support for the `people_append` method.
  [suryasr007]

* Lots of cleanup of legacy assumptions:
  * `profile_sync` method was removed
  * request.user no longer required
  * MixpanelTrack init now accepts `distinct_id` instead of `user`
  * `state` ProfileProperty no longer required
  [zupo]


0.2.1 (2019-07-28)
------------------

* Not all consumers have a .flush() method.
  [zupo]


0.2.0 (2019-07-27)
------------------

* Rewrite based on 5 years of Mixpanel usage in production at Niteo.
  [@zupo, @vanclevstik, @dz0ny, @karantan, @am-on, @rokcarl]


0.1.14 - 0.1.65 (2012-2014)
---------------------------

* Legacy version developed by @hadrien.
