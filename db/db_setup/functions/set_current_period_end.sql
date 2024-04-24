CREATE OR REPLACE FUNCTION user_based.set_current_period_end()
RETURNS TRIGGER AS
$$
BEGIN
	NEW.current_period_end =
	CASE WHEN NEW."period" = 1
		THEN date_add(new."current_period_start"::date, '7 days'::interval)
	WHEN NEW."period" = 2
		THEN
			date_add(new."current_period_start"::date, '30 days'::interval)
	WHEN NEW."period" = 3
		THEN date_add(new."current_period_start"::date, '365 days'::interval)
	ELSE date_add(new."current_period_start"::date, '30 days'::interval)
	END CASE;

	IF new.end_date IS NOT NULL AND NEW.current_period_end::date > new.end_date::date THEN
		new.current_period_end = new.end_date;
	END IF;

	RETURN NEW;
END;
$$
LANGUAGE plpgsql;