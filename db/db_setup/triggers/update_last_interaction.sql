create or replace trigger update_last_interaction
after insert or update on user_based.expense
for each row
execute function shared.update_last_interaction();

create or replace trigger update_last_interaction
after insert or update on user_based.income
for each row
execute function shared.update_last_interaction();

create or replace trigger update_last_interaction
after insert or update on user_based.expense_limit
for each row
execute function shared.update_last_interaction();