options.timeout   = 120
options.subscribe = true
options.expunge   = true

dovecot = IMAP {
    server = 'localhost',
    port = 9143,
    username = 'johnw',
    password = 'pass',
}

_, passwd = pipe_from('pass imap.fastmail.com | head -1')

fastmail = IMAP {
    server = 'imap.fastmail.com',
    username = 'johnw@newartisans.com',
    password = passwd,
    ssl = 'ssl23',
}

messages = fastmail['Archive']:contain_field('List-Id', '<')

   - fastmail['Archive']:contain_to("john.wiegley@baesystems.com")
   - fastmail['Archive']:contain_to("john@wiegley.com")
   - fastmail['Archive']:contain_to("johnw@boostpro.com")
   - fastmail['Archive']:contain_to("johnw@fpcomplete.com")
   - fastmail['Archive']:contain_to("johnw@gnu.org")
   - fastmail['Archive']:contain_to("johnw@hcoop.net")
   - fastmail['Archive']:contain_to("johnw@newartisans.com")
   - fastmail['Archive']:contain_to("jwiegley@gmail.com")
   - fastmail['Archive']:contain_to("jwiegley@hotmail.com")
   - fastmail['Archive']:contain_to("jwiegley@users.sourceforge.net")

   - fastmail['Archive']:contain_cc("john.wiegley@baesystems.com")
   - fastmail['Archive']:contain_cc("john@wiegley.com")
   - fastmail['Archive']:contain_cc("johnw@boostpro.com")
   - fastmail['Archive']:contain_cc("johnw@fpcomplete.com")
   - fastmail['Archive']:contain_cc("johnw@gnu.org")
   - fastmail['Archive']:contain_cc("johnw@hcoop.net")
   - fastmail['Archive']:contain_cc("johnw@newartisans.com")
   - fastmail['Archive']:contain_cc("jwiegley@gmail.com")
   - fastmail['Archive']:contain_cc("jwiegley@hotmail.com")
   - fastmail['Archive']:contain_cc("jwiegley@users.sourceforge.net")

   - fastmail['Archive']:contain_from("john.wiegley@baesystems.com")
   - fastmail['Archive']:contain_from("john@wiegley.com")
   - fastmail['Archive']:contain_from("johnw@boostpro.com")
   - fastmail['Archive']:contain_from("johnw@fpcomplete.com")
   - fastmail['Archive']:contain_from("johnw@gnu.org")
   - fastmail['Archive']:contain_from("johnw@hcoop.net")
   - fastmail['Archive']:contain_from("johnw@newartisans.com")
   - fastmail['Archive']:contain_from("jwiegley@gmail.com")
   - fastmail['Archive']:contain_from("jwiegley@hotmail.com")
   - fastmail['Archive']:contain_from("jwiegley@users.sourceforge.net")

results = Set {}

for _, msg in ipairs(messages) do
    mbox, uid = table.unpack(msg)
    print(uid)
    table.insert(results, msg)

    if #results > 1000
    then
       results:move_messages(fastmail['List-Archive'])
       results = Set {}
    end
end

results:move_messages(fastmail['List-Archive'])
