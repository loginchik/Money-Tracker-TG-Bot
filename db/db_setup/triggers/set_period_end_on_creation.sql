CREATE OR REPLACE TRIGGER set_period_end_on_creation
BEFORE INSERT ON user_based.expense_limit
FOR EACH ROW
EXECUTE FUNCTION user_based.set_current_period_end();