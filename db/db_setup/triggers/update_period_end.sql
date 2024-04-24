CREATE OR REPLACE TRIGGER update_period_end
BEFORE UPDATE OF current_period_start ON user_based.expense_limit
FOR EACH ROW
EXECUTE FUNCTION user_based.set_current_period_end();