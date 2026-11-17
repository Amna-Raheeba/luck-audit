# Luck Audit Report

## Summary

- Total runs: 200
- Successful runs: 175
- Failed runs: 25
- Lucky runs (success without evidence): 85
- Competent runs: 90
- **Luck Rate: 48.6%** (lucky / successful)
- Competent success rate: 45.0%
- Mutating calls: 375 (110 lucky, uninformed-call rate 29.3%)
- **Risk-Weighted Luck Score: 28.1%** (lucky risk weight 197.0 / total 700.0)

## Uninformed rate by risk tier

- irreversible: 32.0% (share of total risk weight: 75.0%)
- reversible: 16.6% (share of total risk weight: 25.0%)

## Uninformed rate by tool

- book_flight: 40.5%
- book_hotel: 16.6%

## Uninformed rate by argument

- book_flight.flight_id: 25.5%
- book_flight.passenger_name: 0.0%
- book_flight.seat: 40.5%
- book_hotel.check_in: 0.0%
- book_hotel.check_out: 0.0%
- book_hotel.guest_name: 0.0%
- book_hotel.hotel_id: 16.6%

## Auditor accuracy (vs injected ground truth)

- Ground-truth labelled arguments: 1300
- Precision: 100.0%
- Recall: 100.0%
- Accuracy: 100.0%

## Lucky runs

- run-001: book_flight (flight_id, seat)
- run-002: book_flight (seat)
- run-006: book_hotel (hotel_id)
- run-010: book_flight (flight_id, seat)
- run-013: book_flight (flight_id, seat)
- run-015: book_hotel (hotel_id)
- run-016: book_flight (flight_id, seat)
- run-020: book_flight (seat)
- run-024: book_hotel (hotel_id)
- run-025: book_flight (flight_id, seat)
- run-026: book_flight (seat)
- run-027: book_hotel (hotel_id)
- run-029: book_flight (seat)
- run-032: book_flight (seat)
- run-036: book_hotel (hotel_id)
- run-038: book_flight (seat)
- run-039: book_hotel (hotel_id)
- run-041: book_flight (seat)
- run-042: book_hotel (hotel_id)
- run-045: book_hotel (hotel_id)
- run-050: book_flight (seat)
- run-052: book_flight (flight_id, seat)
- run-053: book_flight (seat)
- run-055: book_flight (flight_id, seat)
- run-056: book_flight (seat)
- run-062: book_flight (seat)
- run-066: book_hotel (hotel_id)
- run-069: book_hotel (hotel_id)
- run-076: book_flight (flight_id, seat)
- run-077: book_flight (seat)
- run-080: book_flight (seat)
- run-081: book_hotel (hotel_id)
- run-082: book_flight (flight_id, seat)
- run-085: book_flight (flight_id, seat)
- run-086: book_flight (seat)
- run-087: book_hotel (hotel_id)
- run-090: book_hotel (hotel_id)
- run-095: book_flight (seat)
- run-096: book_hotel (hotel_id)
- run-097: book_flight (flight_id, seat)
- run-100: book_flight (flight_id, seat)
- run-101: book_flight (seat)
- run-102: book_hotel (hotel_id)
- run-103: book_flight (flight_id, seat)
- run-104: book_flight (seat)
- run-106: book_flight (flight_id, seat)
- run-108: book_hotel (hotel_id)
- run-109: book_flight (flight_id, seat)
- run-121: book_flight (flight_id, seat)
- run-122: book_flight (seat)
- run-123: book_hotel (hotel_id)
- run-127: book_flight (flight_id, seat)
- run-128: book_flight (seat)
- run-129: book_hotel (hotel_id)
- run-132: book_hotel (hotel_id)
- run-133: book_flight (flight_id, seat)
- run-134: book_flight (seat)
- run-138: book_hotel (hotel_id)
- run-139: book_flight (flight_id, seat)
- run-140: book_flight (seat)
- run-141: book_hotel (hotel_id)
- run-142: book_flight (flight_id, seat)
- run-145: book_flight (flight_id, seat)
- run-146: book_flight (seat)
- run-148: book_flight (flight_id, seat)
- run-149: book_flight (seat)
- run-150: book_hotel (hotel_id)
- run-152: book_flight (seat)
- run-156: book_hotel (hotel_id)
- run-163: book_flight (flight_id, seat)
- run-164: book_flight (seat)
- run-165: book_hotel (hotel_id)
- run-169: book_flight (flight_id, seat)
- run-170: book_flight (seat)
- run-177: book_hotel (hotel_id)
- run-179: book_flight (seat)
- run-182: book_flight (seat)
- run-183: book_hotel (hotel_id)
- run-186: book_hotel (hotel_id)
- run-190: book_flight (flight_id, seat)
- run-191: book_flight (seat)
- run-192: book_hotel (hotel_id)
- run-193: book_flight (flight_id, seat)
- run-194: book_flight (seat)
- run-198: book_hotel (hotel_id)
