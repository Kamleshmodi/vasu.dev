document.addEventListener('DOMContentLoaded', () => {
    const cascades = document.querySelectorAll('[data-address-cascade]');

    cascades.forEach((container) => {
        const optionsUrl = container.dataset.optionsUrl;
        const validationUrl = container.dataset.validationUrl;

        const countryField = container.querySelector('[data-address-role="country"]');
        const stateField = container.querySelector('[data-address-role="state"]');
        const districtField = container.querySelector('[data-address-role="district"]');
        const cityField = container.querySelector('[data-address-role="city"]');
        const postalField = container.querySelector('[data-address-role="postal-code"]');
        const postalStatus = container.querySelector('[data-address-role="postal-status"]');

        if (!countryField || !stateField || !districtField || !cityField || !postalField) {
            return;
        }

        let initialState = container.dataset.initialState || '';
        let initialDistrict = container.dataset.initialDistrict || '';
        let initialCity = container.dataset.initialCity || '';

        const clearOptions = (field, placeholder) => {
            field.innerHTML = '';
            const option = document.createElement('option');
            option.value = '';
            option.textContent = placeholder;
            field.appendChild(option);
        };

        const populateOptions = (field, values, placeholder, selectedValue = '') => {
            clearOptions(field, placeholder);
            values.forEach((value) => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                if (selectedValue && selectedValue === value) {
                    option.selected = true;
                }
                field.appendChild(option);
            });
        };

        const setPostalStatus = (message, isValid) => {
            if (!postalStatus) {
                return;
            }
            postalStatus.textContent = message || '';
            postalStatus.classList.remove('valid', 'invalid');
            if (!message) {
                return;
            }
            postalStatus.classList.add(isValid ? 'valid' : 'invalid');
        };

        const validatePostalCode = async () => {
            const postalCode = postalField.value.trim();
            if (!postalCode) {
                postalField.setCustomValidity('');
                setPostalStatus('', false);
                return true;
            }

            const params = new URLSearchParams({
                country: countryField.value,
                state: stateField.value,
                postal_code: postalCode,
            });

            try {
                const response = await fetch(`${validationUrl}?${params.toString()}`);
                const data = await response.json();
                postalField.setCustomValidity(data.valid ? '' : (data.message || 'Invalid postal code.'));
                setPostalStatus(data.message, data.valid);
                return Boolean(data.valid);
            } catch (error) {
                postalField.setCustomValidity('');
                setPostalStatus('PIN code could not be verified right now.', false);
                return true;
            }
        };
        container.validateDeliveryPostalCode = validatePostalCode;

        const refreshOptions = async ({ keepState = true, keepDistrict = true, keepCity = true } = {}) => {
            const params = new URLSearchParams({
                country: countryField.value,
                state: keepState ? stateField.value : '',
            });

            const response = await fetch(`${optionsUrl}?${params.toString()}`);
            const data = await response.json();

            const nextState = keepState ? (stateField.value || initialState) : '';
            const nextDistrict = keepDistrict ? (districtField.value || initialDistrict) : '';
            const nextCity = keepCity ? (cityField.value || initialCity) : '';

            populateOptions(stateField, data.states || [], 'Select State', nextState);
            populateOptions(districtField, data.districts || [], 'Select District', nextDistrict);
            populateOptions(cityField, data.cities || [], 'Select City', nextCity);

            const supportsCascade = Boolean(data.supports_cascade);
            stateField.disabled = !supportsCascade;
            districtField.disabled = !supportsCascade;
            cityField.disabled = !supportsCascade;

            if (!supportsCascade) {
                setPostalStatus('Delivery location lookup is currently available only for India.', false);
            }
        };

        countryField.addEventListener('change', async () => {
            initialState = '';
            initialDistrict = '';
            initialCity = '';
            await refreshOptions({ keepState: false, keepDistrict: false, keepCity: false });
            await validatePostalCode();
        });

        stateField.addEventListener('change', async () => {
            initialDistrict = '';
            initialCity = '';
            await refreshOptions({ keepState: true, keepDistrict: false, keepCity: false });
            await validatePostalCode();
        });

        postalField.addEventListener('blur', validatePostalCode);
        postalField.addEventListener('input', () => {
            postalField.setCustomValidity('');
            if (!postalField.value.trim()) {
                setPostalStatus('', false);
            }
        });

        refreshOptions({ keepState: true, keepDistrict: true, keepCity: true }).then(() => {
            validatePostalCode();
        });
    });
});
