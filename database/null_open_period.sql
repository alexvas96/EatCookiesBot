SELECT pv.id FROM public.polls as polls, public.polls_votes as pv
WHERE polls.id = pv.poll_id
AND polls.open_period IS NULL
ORDER BY pv.id ASC;
